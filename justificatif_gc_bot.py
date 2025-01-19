from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from datetime import datetime
import os
import uuid

# Dictionnaire pour stocker les données des étudiants
student_data = {}

# Identifiant du canal (remplacez par l'ID réel du canal Telegram)
CHANNEL_ID = -1002270770971  # Remplacez avec l'ID de votre canal Telegram
ARCHIVE_CHANNEL_ID = -1002482642819  # Remplacez avec l'ID de votre canal d'archivage Telegram

# Fonction pour générer un fichier PDF
def generate_justificatif(data, file_path):
    # Génération du PDF
    c = canvas.Canvas(file_path, pagesize=letter)

    # En-tête
    c.setFont("Helvetica-Bold", 14)
    c.drawString(200, 800, "Université AbouBekr Belkaid")
    c.drawString(200, 780, "Faculté de Technologie")
    c.drawString(200, 760, "Département de Génie Civil")

    # Titre centré
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(300, 720, "Justificatif d'absence")

    # Informations de l'étudiant
    c.setFont("Helvetica", 12)
    c.drawString(100, 680, f"Nom : {data['name']}")
    c.drawString(100, 660, f"Prénom : {data['surname']}")
    c.drawString(100, 640, f"Licence/Master/Ingénieur : {data['level']} - {data['year']} {data['option']}")
    c.drawString(100, 620, f"Date d'absence : du {data['start_date']} au {data['end_date']}")

    # Date de génération
    now = datetime.now()
    date_str = now.strftime("Tlemcen, le %d/%m/%Y à %H:%M")
    c.drawString(100, 580, date_str)

    # Identifiant unique
    unique_id = str(uuid.uuid4())
    c.drawString(100, 560, f"Identifiant unique : {unique_id}")

    # Signature (cachet en bas à droite)
    try:
        signature_path = "signature_cachet.png"  # Chemin du fichier image du cachet
        if os.path.exists(signature_path):
            signature = ImageReader(signature_path)
            c.drawImage(signature, 400, 450, width=150, height=80, mask='auto')
        c.drawString(400, 430, "Validé par le Chef de Département")
    except Exception as e:
        print(f"Erreur lors de l'ajout de la signature : {e}")

    c.save()

    return unique_id

# Message d'accueil
async def welcome(update: Update, context):
    await update.message.reply_text(
        "Bienvenue dans le Bot Justificatif d'Absence !\n\n"
        "Ce bot permet de générer un justificatif d'absence pour les étudiants."
        "\n\nPour commencer, veuillez répondre à une série de questions en cliquant sur /start."
    )

# Commande /start
async def start(update: Update, context):
    await update.message.reply_text(
        "Pour obtenir un justificatif d'absence, nous avons besoin des informations suivantes :\n"
        "1. Nom\n"
        "2. Prénom\n"
        "3. Niveau (Licence, Master, Ingénieur)\n"
        "4. Année\n"
        "5. Option\n"
        "6. Date d'absence (du - au, conforme au certificat médical)\n"
        "\nNous allons commencer maintenant. Quel est votre Nom ?"
    )
    user_id = update.message.from_user.id
    student_data[user_id] = {
        "data": None,
        "file": None,
        "name": None,
        "surname": None,
        "level": None,
        "year": None,
        "option": None,
        "start_date": None,
        "end_date": None
    }

# Collecte des informations étape par étape
async def handle_message(update: Update, context):
    user_id = update.message.from_user.id
    text = update.message.text

    if user_id not in student_data:
        await update.message.reply_text("Veuillez d'abord utiliser la commande /start pour commencer.")
        return

    data = student_data[user_id]

    if data["name"] is None:
        data["name"] = text
        await update.message.reply_text("Merci. Quel est votre Prénom ?")
    elif data["surname"] is None:
        data["surname"] = text
        await update.message.reply_text("Merci. Quel est votre Niveau (Licence, Master, Ingénieur) ?")
    elif data["level"] is None:
        data["level"] = text
        await update.message.reply_text("Merci. Quelle est votre Année ?")
    elif data["year"] is None:
        data["year"] = text
        await update.message.reply_text("Merci. Quelle est votre Option ?")
    elif data["option"] is None:
        data["option"] = text
        await update.message.reply_text("Merci. Quelle est la Date d'absence (du - au) ?")
    elif data["start_date"] is None or data["end_date"] is None:
        try:
            start_date, end_date = text.split(" au ")
            data["start_date"] = start_date.strip()
            data["end_date"] = end_date.strip()
            await update.message.reply_text("Merci. Maintenant, envoyez une image de votre justificatif.")
        except ValueError:
            await update.message.reply_text("Format incorrect. Veuillez entrer la date au format : du [date] au [date].")
    else:
        await update.message.reply_text("Vous avez déjà envoyé vos informations. Veuillez attendre la validation.")

# Gérer les images (justificatifs scannés)
async def handle_image(update: Update, context):
    user_id = update.message.from_user.id
    photo = update.message.photo[-1]  # Obtenir la meilleure résolution de l'image

    if user_id in student_data and student_data[user_id]["start_date"] and student_data[user_id]["end_date"]:
        file_path = f"{user_id}_justificatif.jpg"
        telegram_file = await photo.get_file()
        await telegram_file.download_to_drive(file_path)
        student_data[user_id]["file"] = file_path

        # Ajouter des boutons pour validation par le chef de département
        keyboard = [
            [
                InlineKeyboardButton("Valider", callback_data=f"{user_id}_approve"),
                InlineKeyboardButton("Refuser", callback_data=f"{user_id}_decline")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        try:
            # Envoyer au canal Telegram
            await context.bot.send_message(
                chat_id=CHANNEL_ID,
                text=(
                    f"Nouvelle demande de validation:\n\n"
                    f"Nom : {student_data[user_id]['name']}\n"
                    f"Prénom : {student_data[user_id]['surname']}\n"
                    f"Niveau : {student_data[user_id]['level']} - {student_data[user_id]['year']} {student_data[user_id]['option']}\n"
                    f"Date d'absence : du {student_data[user_id]['start_date']} au {student_data[user_id]['end_date']}\n"
                ),
                reply_markup=reply_markup
            )
            await context.bot.send_photo(chat_id=CHANNEL_ID, photo=open(file_path, "rb"))
            await update.message.reply_text(
                "Votre justificatif a été transmis pour validation. Une fois validé, pensez à l'envoyer par Teams ou par email à vos enseignants concernés."
            )
        except Exception as e:
            await update.message.reply_text(f"Erreur lors de l'envoi au canal : {e}")
    else:
        await update.message.reply_text("Veuillez d'abord compléter vos informations avant de télécharger une image.")

# Validation ou refus du justificatif par le chef de département
async def validate(update: Update, context):
    query = update.callback_query
    await query.answer()
    user_id, action = query.data.split("_")
    user_id = int(user_id)

    if action == "approve":
        # Récupérer les données de l'étudiant
        data = student_data.get(user_id, {})
        if data:
            # Générer un justificatif
            pdf_path = f"{user_id}_justificatif.pdf"
            unique_id = generate_justificatif(
                {
                    "name": data["name"],
                    "surname": data["surname"],
                    "level": data["level"],
                    "year": data["year"],
                    "option": data["option"],
                    "start_date": data["start_date"],
                    "end_date": data["end_date"]
                },
                pdf_path
            )

            # Envoyer le justificatif à l'étudiant
            await context.bot.send_document(chat_id=user_id, document=open(pdf_path, "rb"))
            await query.edit_message_text("Justificatif validé, et l'étudiant a été notifié.")

            # Archiver dans le canal d'archivage
            now = datetime.now()
            archive_message = (
                f"Justificatif archivé:\n\n"
                f"Nom : {data['name']}\n"
                f"Prénom : {data['surname']}\n"
                f"Identifiant unique : {unique_id}\n"
                f"Validé le : {now.strftime('%d/%m/%Y à %H:%M')}"
            )
            await context.bot.send_message(chat_id=ARCHIVE_CHANNEL_ID, text=archive_message)

            # Supprimer le fichier local après envoi
            os.remove(pdf_path)
        else:
            await query.edit_message_text("Erreur : données de l'étudiant introuvables.")
    elif action == "decline":
        await context.bot.send_message(chat_id=user_id, text="Votre justificatif a été refusé.")
        await query.edit_message_text("Le justificatif a été refusé.")

# Configurer le bot
def main():
    import os
    TOKEN = os.getenv("TELEGRAM_TOKEN")

    application = Application.builder().token(TOKEN).build()

    # Ajouter les gestionnaires de commandes et de messages
    application.add_handler(CommandHandler("welcome", welcome))
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.PHOTO, handle_image))
    application.add_handler(CallbackQueryHandler(validate))

    # Lancer le bot
    application.run_polling()

if __name__ == "__main__":
    main()
