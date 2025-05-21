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

# Configuración de logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Estados de la conversación
ELEGIR_ACCION, ELEGIR_TIPO, ELEGIR_CATEGORIA, ELEGIR_CONCEPTO, INGRESAR_MONTO, CONFIRMAR = range(6)

# Listas predefinidas
CONCEPTOS_INGRESOS = [
    "SUELDO",
    "VENTA DE PRODUCTOS",
    "EXTRAS",
    "COBRO DE DEUDAS",
    "OTROS"
]

CONCEPTOS_GASTOS = [
    "CUOTA DEPARTAMENTO",
    "TARJETA DE CREDITO",
    "PLAN DE CELULAR",
    "INTERNET",
    "LUZ",
    "MANTENIMIENTO",
    "GAS",
    "PASAJES",
    "GASOLINA/COMBUSTIBLE",
    "DIEZMO",
    "OFRENDA",
    "AHORROS",
    "ALIMENTOS / COMIDA (DESAYUNO, ALMUERZO, CENA)",
    "ROPA",
    "CALZADO / ZAPATILLA / ZAPATO",
    "ARTICULOS DE COCINA",
    "ARTICULOS DE LIMPIEZA",
    "ARTICULO PARA EL HOGAR",
    "COSAS NO NECESARIAS",
    "ARTICULOS DE ASEO PERSONAL",
    "REGALOS",
    "TECNOLOGIA",
    "ELECTRODOMESTICOS",
    "CITA MEDICA",
    "GASTOS MEDICOS",
    "MEDICINA / PASTILLAS",
    "SALIDAS",
    "LIBROS",
    "ANIVERSARIO",
    "DONACION",
    "DENTISTA",
    "VIAJES / PASEOS",
    "PRESTAMOS"
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
    """Procesa mensajes de texto con formato: TIPO MONTO CONCEPTO"""
    text = update.message.text.upper()
    user = update.effective_user
    
    try:
        parts = text.split()
        
        # Verificar si el formato es correcto
        if len(parts) < 3:
            await update.message.reply_text(
                "❌ Formato incorrecto. Usa: TIPO MONTO CONCEPTO\n"
                "Ejemplo: GASTO 50 ALIMENTOS"
            )
            return
        
        tipo = parts[0]
        if tipo not in TIPOS:
            await update.message.reply_text(f"❌ El tipo debe ser INGRESO o GASTO. Recibido: {tipo}")
            return
        
        try:
            monto = float(parts[1].replace(',', '.'))
            if monto <= 0:
                await update.message.reply_text("❌ El monto debe ser mayor que cero.")
                return
        except ValueError:
            await update.message.reply_text("❌ El monto debe ser un número válido.")
            return
        
        # Unir el resto como concepto
        concepto_texto = " ".join(parts[2:])
        
        # Verificar si el concepto existe en las listas predefinidas
        lista_conceptos = CONCEPTOS_INGRESOS if tipo == "INGRESO" else CONCEPTOS_GASTOS
        
        # Buscar el mejor concepto que coincida
        concepto_encontrado = None
        for concepto in lista_conceptos:
            if concepto_texto in concepto or concepto in concepto_texto:
                concepto_encontrado = concepto
                break
        
        if not concepto_encontrado:
            # Si no se encuentra una coincidencia exacta, mostrar opciones
            await update.message.reply_text(
                f"❌ No se encontró el concepto '{concepto_texto}'. Por favor, usa el comando /start para registrar."
            )
            return
        
        # Categoría por defecto (se puede mejorar con un algoritmo más inteligente)
        categoria = "VARIABLE"  # Por defecto
        
        # Algunos conceptos que suelen ser fijos
        conceptos_fijos = ["CUOTA DEPARTAMENTO", "INTERNET", "LUZ", "MANTENIMIENTO", "GAS", "PLAN DE CELULAR", 
                         "SUELDO", "AHORROS", "DIEZMO","OFRENDA"]
        
        for cf in conceptos_fijos:
            if cf in concepto_encontrado:
                categoria = "FIJO"
                break
        
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

    # 1. Obtener TOKEN del bot de variables de entorno (OBLIGATORIO para seguridad)
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    if not TOKEN:
        logger.error("Error: La variable de entorno TELEGRAM_BOT_TOKEN no está configurada.")
        logger.error("Por favor, configura tu token de bot de Telegram en Render como una variable de entorno.")
        # Es crucial que el bot no se inicie sin el token
        raise ValueError("TELEGRAM_BOT_TOKEN no configurado.")

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
    
    # Manejador para registro por texto
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, registrar_por_texto)) # Añadir a application
    
    # Otros comandos
    application.add_handler(CommandHandler("ayuda", ayuda)) # Añadir a application
    
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
