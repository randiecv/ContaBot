import logging
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
# Importar Application, Request y URLInputFile para usar con webhooks en versiones recientes de python-telegram-bot
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackContext, ConversationHandler, CallbackQueryHandler
from telegram.ext import filters # Importa el módulo 'filters' aparte
# No necesitamos Updater con Application.run_webhook
# from telegram.ext import Updater
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import os
import json # Necesario para cargar las credenciales de Google Sheets desde JSON string
import google.generativeai as genai
from PIL import Image # Necesitas Pillow para esto
import io

# **Importante:** Estas variables se inicializarán más tarde en main()
# Las declaramos aquí para que sean globales y accesibles desde cualquier función.
gemini_text_model = None
gemini_vision_model = None # Si vas a usar gemini-pro-vision

# Configuración de logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Estados de la conversación
ELEGIR_ACCION, ELEGIR_TIPO, ELEGIR_CATEGORIA, ELEGIR_CONCEPTO, INGRESAR_MONTO, CONFIRMAR = range(6)

# Listas predefinidas
CONCEPTOS_INGRESOS = [
    "SUELDO",
    "CTS",
    "GRATIFICACIÓN",
    "AFP",
    "VENTA DE PRODUCTOS",
    "MANICURE",
    "COBRO DE DEUDAS",
    "REGALOS",
    "OTROS"
]

CONCEPTOS_GASTOS = [
    "CUOTA DEPARTAMENTO",
    "TARJETA DE CREDITO",
    "PLAN DE CELULAR",
    "INTERNET",
    "LUZ",
    "MANTENIMIENTO DE DEPARTAMENTO",
    "GAS",
    "PASAJES",
    "GASOLINA/COMBUSTIBLE",
    "DIEZMO",
    "OFRENDA",
    "AHORROS",
    "ALIMENTOS/COMIDA(DESAYUNO,ALMUERZO,CENA)",
    "ROPA",
    "CALZADO/ZAPATILLA/ZAPATO",
    "ARTICULOS DE COCINA",
    "ARTICULOS DE LIMPIEZA",
    "ARTICULO PARA EL HOGAR",
    "OTROS GASTOS",
    "ARTICULOS DE ASEO PERSONAL",
    "REGALOS",
    "TECNOLOGIA",
    "ELECTRODOMESTICOS",
    "CITA MEDICA",
    "GASTOS MEDICOS",
    "MEDICINA/PASTILLAS",
    "SALIDAS",
    "LIBROS",
    "ANIVERSARIO",
    "DONACION",
    "DENTISTA",
    "VIAJES/PASEOS",
    "PRESTAMOS",
    "GUSTITOS",
    "REPARACIONES/MEJORAS",
    "DEUDA"
]

CATEGORIAS = ["FIJO", "VARIABLE"]
TIPOS = ["INGRESO", "GASTO"]

# Variables para almacenar temporalmente la información del registro
usuario_data = {}

# Función para conectar con Google Sheets
def conectar_google_sheets():
    scope = ["https://spreadsheets.google.com/feeds",
             "https://www.googleapis.com/auth/spreadsheets",
             "https://www.googleapis.com/auth/drive.file",
             "https://www.googleapis.com/auth/drive"]

    credentials_json_str = os.getenv('GOOGLE_CREDENTIALS_JSON') # El nombre de la variable que usaste en Render

    if not credentials_json_str:
        logger.error("¡La variable de entorno 'GOOGLE_CREDENTIALS_JSON' no está configurada o está vacía!")
        logger.error("Asegúrate de haber pegado el contenido completo del JSON de la clave de servicio en Render.")
        return None
    
    try:
        # Cargar las credenciales desde la cadena JSON de la variable de entorno
        creds_dict = json.loads(credentials_json_str)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        logger.info("Credenciales cargadas correctamente desde la variable de entorno.")
        
        client = gspread.authorize(creds)
        logger.info("Cliente autorizado correctamente")
        
        # Nombre de tu hoja de Google Sheets
        nombre_spreadsheet = "ECONOMIA DE LA CASA"
        logger.info(f"Intentando abrir la hoja: {nombre_spreadsheet}")
        
        # Listar todas las hojas a las que tenemos acceso
        disponibles = [sheet.title for sheet in client.openall()]
        logger.info(f"Hojas disponibles: {disponibles}")
        
        spreadsheet = client.open(nombre_spreadsheet)
        logger.info(f"Hoja de cálculo abierta correctamente. Hojas: {[ws.title for ws in spreadsheet.worksheets()]}")
        
        sheet = spreadsheet.worksheet("Registro")
        logger.info("Hoja 'Registro' abierta correctamente")
        
        return sheet
    except Exception as e:
        logger.error(f"Error al conectar con Google Sheets: {str(e)}")
        logger.error(f"Tipo de error: {type(e).__name__}")
        import traceback
        logger.error(f"Detalles: {traceback.format_exc()}")
        return None

# Comandos
async def start_command(update: Update, context: CallbackContext) -> int: # Renombrado para evitar conflicto con main.py/start
    user = update.effective_user
    keyboard = [
        [InlineKeyboardButton("Registrar movimiento", callback_data='registrar')],
        [InlineKeyboardButton("Ver último registro", callback_data='ver_ultimo')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f'Hola {user.first_name}! Soy el bot de economía familiar.\n\n'
        f'¿Qué deseas hacer?',
        reply_markup=reply_markup
    )
    
    return ELEGIR_ACCION

async def elegir_accion(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    
    if query.data == 'registrar':
        # Inicializar datos del usuario
        usuario_data[query.from_user.id] = {
            'usuario': query.from_user.first_name
        }
        
        keyboard = [[InlineKeyboardButton(tipo, callback_data=tipo)] for tipo in TIPOS]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text="¿Qué tipo de movimiento quieres registrar?",
            reply_markup=reply_markup
        )
        return ELEGIR_TIPO
    
    elif query.data == 'ver_ultimo':
        # Implementar la visualización del último registro
        try:
            sheet = conectar_google_sheets()
            if sheet:
                # Obtener la última fila
                records = sheet.get_all_records()
                if records:
                    last_record = records[-1]
                    await query.edit_message_text(
                        f"📝 *Último registro*\n\n"
                        f"📅 Fecha: {last_record.get('Fecha', 'N/A')}\n"
                        f"👤 Usuario: {last_record.get('Usuario', 'N/A')}\n"
                        f"📊 Tipo: {last_record.get('Tipo', 'N/A')}\n"
                        f"🏷️ Categoría: {last_record.get('Categoría', 'N/A')}\n"
                        f"🔖 Concepto: {last_record.get('Concepto', 'N/A')}\n"
                        f"💰 Monto: S/. {last_record.get('Monto', 'N/A')}\n",
                        parse_mode='Markdown'
                    )
                else:
                    await query.edit_message_text("No hay registros disponibles.")
            else:
                await query.edit_message_text("No se pudo conectar con la hoja de cálculo.")
        except Exception as e:
            await query.edit_message_text(f"Error al obtener el último registro: {e}")
        
        return ConversationHandler.END

async def elegir_tipo(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    
    tipo = query.data
    usuario_data[query.from_user.id]['tipo'] = tipo
    
    keyboard = [[InlineKeyboardButton(categoria, callback_data=categoria)] for categoria in CATEGORIAS]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=f"Has seleccionado: {tipo}\n\n¿Es un {tipo.lower()} fijo o variable?",
        reply_markup=reply_markup
    )
    
    return ELEGIR_CATEGORIA

async def elegir_categoria(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    
    categoria = query.data
    usuario_data[query.from_user.id]['categoria'] = categoria
    
    # Seleccionar la lista adecuada según el tipo
    conceptos = CONCEPTOS_INGRESOS if usuario_data[query.from_user.id]['tipo'] == "INGRESO" else CONCEPTOS_GASTOS
    
    # Crear botones en filas de 2
    keyboard = []
    row = []
    for i, concepto in enumerate(conceptos):
        row.append(InlineKeyboardButton(concepto, callback_data=concepto))
        if i % 2 == 1 or i == len(conceptos) - 1:
            keyboard.append(row)
            row = []
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=f"Has seleccionado: {categoria}\n\nSelecciona el concepto:",
        reply_markup=reply_markup
    )
    
    return ELEGIR_CONCEPTO

async def elegir_concepto(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    
    concepto = query.data
    usuario_data[query.from_user.id]['concepto'] = concepto
    
    await query.edit_message_text(
        text=f"Has seleccionado: {concepto}\n\nPor favor, ingresa el monto (solo números):"
    )
    
    return INGRESAR_MONTO

async def ingresar_monto(update: Update, context: CallbackContext) -> int:
    try:
        monto = float(update.message.text.replace(',', '.'))
        user_id = update.effective_user.id
        
        if monto <= 0:
            await update.message.reply_text("El monto debe ser mayor que cero. Por favor, ingresa un monto válido:")
            return INGRESAR_MONTO
        
        usuario_data[user_id]['monto'] = monto
        
        # Mostrar resumen para confirmación
        keyboard = [
            [InlineKeyboardButton("✅ Confirmar", callback_data='confirmar')],
            [InlineKeyboardButton("❌ Cancelar", callback_data='cancelar')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"📝 *Resumen del registro*\n\n"
            f"👤 Usuario: {usuario_data[user_id]['usuario']}\n"
            f"📊 Tipo: {usuario_data[user_id]['tipo']}\n"
            f"🏷️ Categoría: {usuario_data[user_id]['categoria']}\n"
            f"🔖 Concepto: {usuario_data[user_id]['concepto']}\n"
            f"💰 Monto: S/. {monto}\n\n"
            f"¿Confirmas este registro?",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        return CONFIRMAR
    
    except ValueError:
        await update.message.reply_text("Por favor, ingresa solo números (usa punto o coma para decimales):")
        return INGRESAR_MONTO

async def confirmar(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    
    if query.data == 'confirmar':
        user_id = query.from_user.id
        
        try:
            sheet = conectar_google_sheets()
            if sheet:
                # Datos a registrar
                fecha = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                mes = datetime.now().strftime("%B %Y")  # Mes y año
                
                # Añadir a Google Sheets
                sheet.append_row([
                    fecha,
                    usuario_data[user_id]['usuario'],
                    usuario_data[user_id]['tipo'],
                    usuario_data[user_id]['categoria'],
                    usuario_data[user_id]['concepto'],
                    usuario_data[user_id]['monto'],
                    mes
                ])
                
                await query.edit_message_text("✅ Registro completado con éxito.")
            else:
                await query.edit_message_text("❌ No se pudo conectar con la hoja de cálculo.")
        
        except Exception as e:
            await query.edit_message_text(f"❌ Error al guardar el registro: {e}")
    
    else:  # cancelar
        await query.edit_message_text("❌ Registro cancelado.")
    
    # Limpiar datos
    if user_id in usuario_data:
        del usuario_data[user_id]
    
    return ConversationHandler.END

async def registrar_por_texto(update: Update, context: CallbackContext) -> None:
    """
    Procesa mensajes de texto usando Gemini para extraer información.
    """
    user_message = update.message.text.upper() # Convertir a mayúsculas para consistencia con tus listas

    # --- AQUI ES DONDE INTEGRARÁS GEMINI ---
    try:
        # Definir el prompt para Gemini
        # Queremos que Gemini extraiga el tipo, monto y concepto
        # y categorice como FIJO o VARIABLE si es posible, o use un default.
        # Le pedimos que nos devuelva un JSON para facilitar el parseo.
        prompt = f"""
        Analiza el siguiente mensaje para extraer la siguiente información en formato JSON:
        - "tipo": "INGRESO" o "GASTO"
        - "monto": solo el número (flotante), si no se encuentra, usar 0.0
        - "concepto": la descripción del gasto/ingreso, debe ser uno de los siguientes si coincide: {", ".join(CONCEPTOS_INGRESOS + CONCEPTOS_GASTOS)}. Si no hay coincidencia exacta, usa la descripción más cercana o la que puedas inferir.
        - "categoria": "FIJO" o "VARIABLE". Intenta inferir si es fijo o variable basado en el concepto o la naturaleza de la transacción. Si no es claro, asume "VARIABLE".
        - "fecha": si se menciona una fecha específica (ayer, lunes, 25/05, etc.), calcúlala y devuélvela en formato DD/MM/YYYY. Si no se menciona fecha, usa "actual"

        Si el monto no se puede determinar, devuelve un JSON con un campo "error": "Monto no válido".

        Ejemplos de cómo debería ser el JSON:
        Mensaje: "Gaste 30 soles en pasajes"
        JSON: {{"tipo": "GASTO", "monto": 30.0, "concepto": "PASAJES", "categoria": "VARIABLE"}}

        Mensaje: "Mi sueldo de 1500"
        JSON: {{"tipo": "INGRESO", "monto": 1500.0, "concepto": "SUELDO", "categoria": "FIJO"}}

        Mensaje: "Compre ropa por 80"
        JSON: {{"tipo": "GASTO", "monto": 80.0, "concepto": "ROPA", "categoria": "VARIABLE"}}
        
        "Gasté 30 soles en pasajes ayer" -> {{"fecha": "01/06/2025", ...}}
        "El lunes pagué 100 de luz" -> {{"fecha": "fecha_del_lunes", ...}}
        "Compré ropa por 80" -> {{"fecha": "actual", ...}}

        Mensaje a analizar: "{user_message}"
        """
        
        # Generar contenido con Gemini
        # temp = 0.2 para respuestas más determinísticas, menos creativas
        response = gemini_text_model.generate_content(prompt, generation_config={"temperature": 0.2})
        
        # Extraer el texto de la respuesta y cargarlo como JSON
        # A veces Gemini puede añadir texto extra, intentamos limpiar si es necesario
        response_text = response.text.strip().replace("```json", "").replace("```", "")
        
        extracted_data = json.loads(response_text)
        
        # Verificar si Gemini reportó un error de monto
        if "error" in extracted_data:
            await update.message.reply_text(f"❌ {extracted_data['error']}. Por favor, asegúrate de incluir un monto válido.")
            return

        tipo = extracted_data.get('tipo', 'GASTO') # Default a GASTO si Gemini no lo infiere bien
        monto = float(extracted_data.get('monto', 0.0))
        concepto_encontrado = extracted_data.get('concepto', 'OTROS')
        categoria = extracted_data.get('categoria', 'VARIABLE') # Default a VARIABLE

        user = update.effective_user

        # Validaciones básicas que aún pueden ser útiles después de Gemini
        if monto <= 0:
            await update.message.reply_text("❌ El monto debe ser mayor que cero.")
            return
        
        if tipo not in TIPOS: # Asegurarse que Gemini devolvió un tipo válido
            await update.message.reply_text(f"❌ No pude determinar si es INGRESO o GASTO. Recibí: {tipo}. Por favor, sé más específico o usa /start.")
            return
        
        if categoria not in CATEGORIAS: # Asegurarse que Gemini devolvió una categoría válida
             categoria = "VARIABLE" # Fallback si Gemini no devuelve FIJO o VARIABLE

        # --- FIN DE LA INTEGRACIÓN DE GEMINI ---
        
        # Registrar en Google Sheets
        sheet = conectar_google_sheets()
        if sheet:
            fecha = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            mes = datetime.now().strftime("%B %Y")
            
            sheet.append_row([
                fecha,
                user.first_name,
                tipo,
                categoria,
                concepto_encontrado,
                monto,
                mes
            ])
            
            await update.message.reply_text(
                f"✅ Registro rápido completado:\n\n"
                f"👤 Usuario: {user.first_name}\n"
                f"📊 Tipo: {tipo}\n"
                f"🏷️ Categoría: {categoria}\n"
                f"🔖 Concepto: {concepto_encontrado}\n"
                f"💰 Monto: S/. {monto}\n"
            )
        else:
            await update.message.reply_text("❌ No se pudo conectar con la hoja de cálculo.")
    
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def procesar_recibo_con_gemini(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    await update.message.reply_text("Detecté una imagen. Intentando analizarla como un recibo...")

    try:
        # Descargar la imagen
        photo_file = await update.message.photo[-1].get_file() # Obtener la foto de mayor resolución
        photo_bytes = await photo_file.download_as_bytearray()

        # Convertir a formato de imagen para Pillow y luego para Gemini
        # Esto es necesario porque Gemini espera un objeto Image de PIL
        img = Image.open(io.BytesIO(photo_bytes))

        # Prompt para Gemini Vision
        # Aquí la clave es ser muy específico sobre qué quieres extraer del recibo
        prompt_parts = [
            "Extrae el monto total, la fecha (en formato DD/MM/YYYY), y sugiere una categoría de gasto de este recibo. Si no encuentras una fecha válida, usa 'sin_fecha'. Devuelve la información en formato JSON.",
            img
        ]

        response = gemini_vision_model.generate_content(prompt_parts)

        # Limpiar y parsear la respuesta JSON de Gemini
        response_text = response.text.strip().replace("```json", "").replace("```", "")
        extracted_data = json.loads(response_text)

        # Usar los datos extraídos por Gemini
        monto_recibo = float(extracted_data.get('monto_total', 0.0))
        
        # Obtener fecha de Gemini o usar fecha actual como fallback
        fecha_gemini = extracted_data.get('fecha', 'actual')
        if fecha_gemini == 'actual':
            fecha_registro = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        else:
            # Usar fecha de Gemini + hora actual
            fecha_registro = fecha_gemini + " " + datetime.now().strftime("%H:%M:%S")
        
        categoria_recibo = extracted_data.get('categoria', 'Otros') # Fallback si Gemini no categoriza

        # Aquí podrías preguntar al usuario para confirmar o ajustar los datos
        # Por simplicidad, lo guardamos directamente

        sheet = conectar_google_sheets()
        if sheet:
            # Asumimos que los recibos son gastos, pero Gemini podría inferirlo si el prompt es más complejo
            tipo_recibo = "GASTO" 
            # Podrías tener una lógica más sofisticada para la categoría Fija/Variable
            categoria_final = "VARIABLE" # Por defecto, o intentar mapear la categoría de Gemini a tus CATEGORIAS

            sheet.append_row([
                fecha_registro,
                user.first_name,
                tipo_recibo,
                categoria_final, # La categoría inferida por Gemini o un default
                f"Gasto por recibo: {categoria_recibo}", # Una descripción más detallada
                monto_recibo,
                datetime.now().strftime("%B %Y")  # Usar siempre la fecha actual para el mes
            ])

            await update.message.reply_text(
                f"✅ Recibo analizado y registrado:\n\n"
                f"📅 Fecha: {fecha_recibo}\n"
                f"💰 Monto: S/. {monto_recibo}\n"
                f"🏷️ Categoría sugerida: {categoria_recibo}\n"
                f"Puedes usar /start para un registro más detallado."
            )
        else:
            await update.message.reply_text("❌ No se pudo conectar con la hoja de cálculo para registrar el recibo.")

    except json.JSONDecodeError:
        logger.error(f"Error al decodificar JSON de Gemini Vision: {response.text}")
        await update.message.reply_text("❌ No pude extraer la información del recibo. ¿Es una imagen clara de un recibo?")
    except Exception as e:
        logger.error(f"Error al procesar recibo con Gemini: {e}")
        await update.message.reply_text(f"❌ Ocurrió un error al procesar la imagen: {e}")


async def cancelar(update: Update, context: CallbackContext) -> int:
    """Cancela la conversación"""
    user = update.message.from_user
    logger.info(f"Usuario {user.first_name} canceló la conversación.")
    await update.message.reply_text('Operación cancelada. ¡Hasta pronto!')
    
    # Limpiar datos
    if update.effective_user.id in usuario_data:
        del usuario_data[update.effective_user.id]
    
    return ConversationHandler.END

async def ayuda(update: Update, context: CallbackContext) -> None:
    """Envía un mensaje de ayuda"""
    await update.message.reply_text(
        "🤖 *Bot de Economía Familiar* 🏡\n\n"
        "*Comandos disponibles:*\n"
        "/start - Iniciar el bot y registrar un movimiento\n"
        "/ayuda - Mostrar este mensaje de ayuda\n\n"
        "*Registro rápido por texto:*\n"
        "Puedes escribir directamente en este formato:\n"
        "TIPO MONTO CONCEPTO\n\n"
        "*Ejemplos:*\n"
        "• INGRESO 1500 SUELDO\n"
        "• GASTO 50 ALIMENTOS\n",
        parse_mode='Markdown'
    )

async def error(update: Update, context: CallbackContext) -> None:
    """Maneja errores"""
    logger.warning(f'Update {update} causó el error {context.error}')
    if update.message:
        await update.message.reply_text("Ocurrió un error. Por favor, intenta de nuevo o contacta al administrador.")

def main() -> None:
    """Función principal"""
    # --- CAMBIOS AQUÍ para configurar Webhooks ---
    global gemini_text_model, gemini_vision_model

    # 1. Obtener TOKEN del bot de variables de entorno (OBLIGATORIO para seguridad)
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    if not TOKEN:
        logger.error("Error: La variable de entorno TELEGRAM_BOT_TOKEN no está configurada.")
        logger.error("Por favor, configura tu token de bot de Telegram en Render como una variable de entorno.")
        # Es crucial que el bot no se inicie sin el token
        raise ValueError("TELEGRAM_BOT_TOKEN no configurado.")
    
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    if not GEMINI_API_KEY:
        logger.error("Error: La variable de entorno GEMINI_API_KEY no está configurada.")
        raise ValueError("GEMINI_API_KEY no configurada.")
    genai.configure(api_key=GEMINI_API_KEY)
     # --- AÑADE ESTA LÍNEA PARA VERIFICAR ---
    logger.info(f"GEMINI_API_KEY cargada (solo los primeros 5 caracteres): {GEMINI_API_KEY[:5]}*****")
    # --- FIN DE LA LÍNEA DE VERIFICACIÓN ---
    # Puedes definir el modelo aquí o en la función donde lo uses
    #model_text = genai.GenerativeModel('gemini-pro') 
    #model_vision = genai.GenerativeModel('gemini-pro-vision')
    #gemini_text_model = genai.GenerativeModel('gemini-pro')

    gemini_text_model = genai.GenerativeModel('gemini-1.5-flash')
    
    if os.getenv("ENABLE_RECEIPT_PROCESSING", "False").lower() == "true":
        gemini_vision_model = genai.GenerativeModel('gemini-1.5-flash')
    else:
        gemini_vision_model = None


    # Para el modelo de visión, solo inicializa si ENABLE_RECEIPT_PROCESSING está activado
    if os.getenv("ENABLE_RECEIPT_PROCESSING", "False").lower() == "true":
        gemini_vision_model = genai.GenerativeModel('gemini-1.5-flash')
    else:
        gemini_vision_model = None # Asegurarse de que sea None si no se usa

    # 2. Obtener el puerto que Render asigna a tu aplicación (OBLIGATORIO para Web Services)
    PORT = int(os.environ.get("PORT", "8080")) # Default a 8080 si no se especifica (aunque Render lo debería dar)

    # 3. Obtener la URL externa de tu servicio en Render (Render la inyecta automáticamente)
    WEBHOOK_URL = os.getenv("RENDER_EXTERNAL_URL")
    if not WEBHOOK_URL:
        logger.error("Error: La variable de entorno RENDER_EXTERNAL_URL no está configurada.")
        logger.error("Asegúrate de que tu servicio en Render sea un 'Web Service'.")
        raise ValueError("RENDER_EXTERNAL_URL no configurada.")

    # 4. Definir una ruta secreta para el webhook. Se recomienda usar el TOKEN del bot.
    WEBHOOK_PATH = TOKEN # O puedes usar algo como "mi_ruta_secreta_para_webhook"

    # Construye la aplicación del bot
    # Si te encuentras con problemas de 'Request' o 'URLInputFile', puedes añadir:
    # from telegram.request import Request
    # request = Request(con_proxy=False, pool_timeout=60.0)
    # application = Application.builder().token(TOKEN).request(request).build()
    application = Application.builder().token(TOKEN).build()
    
    # Manejador de conversación para el registro de movimientos
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start_command)], # Usar start_command
        states={
            ELEGIR_ACCION: [CallbackQueryHandler(elegir_accion)],
            ELEGIR_TIPO: [CallbackQueryHandler(elegir_tipo)],
            ELEGIR_CATEGORIA: [CallbackQueryHandler(elegir_categoria)],
            ELEGIR_CONCEPTO: [CallbackQueryHandler(elegir_concepto)],
            INGRESAR_MONTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, ingresar_monto)],
            CONFIRMAR: [CallbackQueryHandler(confirmar)]
        },
        fallbacks=[CommandHandler('cancelar', cancelar)]
    )
    
    application.add_handler(conv_handler) # Añadir a application
    
    application.add_handler(MessageHandler(filters.PHOTO & ~filters.COMMAND, procesar_recibo_con_gemini))
    
    # Otros comandos explícitos
    application.add_handler(CommandHandler("ayuda", ayuda))# Añadir a application
    application.add_handler(CommandHandler("cancelar", cancelar)) # También como comando directo fuera de la conv.

    # Manejador para fotos (si lo implementas)
    application.add_handler(MessageHandler(filters.PHOTO & ~filters.COMMAND, procesar_recibo_con_gemini))

    # Manejador para registro por texto
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, registrar_por_texto)) # Añadir a application
    
    # Manejador de errores
    application.add_error_handler(error) # Añadir a application
    
    # Iniciar el bot con Webhooks
    # Primero, asegúrate de que no haya un webhook antiguo configurado en Telegram
    logger.info("Intentando eliminar cualquier webhook anterior.")
	# Importante: set_webhook es una coroutine, pero se llama fuera de un async def,
    # por lo que necesita ser "await" de alguna manera.
    # En este contexto de main(), que no es async, python-telegram-bot
    # lo maneja internamente al llamar run_webhook que inicia el bucle de eventos.
    # Así que, por ahora, no es necesario 'await' aquí directamente.
    application.bot.set_webhook(url=None) # Desactivar webhook si existe uno configurado previamente

    # Configurar el nuevo webhook con la URL de Render
    # 'listen' debe ser "0.0.0.0" para que Render pueda enrutar el tráfico
    # 'port' debe ser el puerto que Render asigna a tu aplicación (desde la variable de entorno)
    # 'url_path' es la parte final de la URL del webhook, se recomienda que sea secreta (ej. el token)
    application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=WEBHOOK_PATH,
        webhook_url=f"{WEBHOOK_URL}/{WEBHOOK_PATH}"
    )

    logger.info(f"Bot iniciado con webhook en: {WEBHOOK_URL}/{WEBHOOK_PATH}")
    logger.info(f"Escuchando en puerto: {PORT}")

if __name__ == '__main__':
    main()
