from flask import Flask, request
from twilio.rest import Client
from google.oauth2 import service_account
from googleapiclient.discovery import build
import datetime

app = Flask(__name__)

# Configuración de Twilio
account_sid = 'AC03f48d42b5645a45077eb5d52bd2c867'
auth_token = 'd1b456713bbbb7d39d4df32d9323b6a8'
twilio_client = Client(account_sid, auth_token)

# Configuración de Google Calendar
creds = service_account.Credentials.from_service_account_file(
    'credentials.json', scopes=['https://www.googleapis.com/auth/calendar'])
calendar_service = build('calendar', 'v3', credentials=creds)

# ID del calendario (puede ser el ID del calendario principal o un calendario secundario)
calendar_id = 'primary'

# Zona horaria de Argentina
TIMEZONE = 'America/Argentina/Buenos_Aires'

# Función para enviar mensajes de WhatsApp con botones
def enviar_mensaje_con_botones(numero, mensaje, botones):
    message = twilio_client.messages.create(
        body=mensaje,
        from_='whatsapp:+541135032234',  # Tu número de Twilio para WhatsApp
        to=f'whatsapp:{numero}',
        persistent_action=botones
    )
    return message.sid

# Función para crear un evento en Google Calendar
def crear_evento(summary, description, start_time, end_time, numero_paciente):
    evento = {
        'summary': summary,
        'description': description,
        'start': {
            'dateTime': start_time,
            'timeZone': TIMEZONE,
        },
        'end': {
            'dateTime': end_time,
            'timeZone': TIMEZONE,
        },
        'attendees': [
            {'email': f'{numero_paciente}@example.com'},  # Usar un email ficticio o válido
        ],
        'reminders': {
            'useDefault': False,
            'overrides': [
                {'method': 'email', 'minutes': 24 * 60},
                {'method': 'popup', 'minutes': 10},
            ],
        },
    }
    evento = calendar_service.events().insert(calendarId=calendar_id, body=evento).execute()
    return evento['id']

# Función para actualizar un evento en Google Calendar
def actualizar_evento(event_id, status):
    evento = calendar_service.events().get(calendarId=calendar_id, eventId=event_id).execute()
    evento['description'] = f'Status: {status}'
    updated_event = calendar_service.events().update(calendarId=calendar_id, eventId=event_id, body=evento).execute()
    return updated_event['id']

# Función para eliminar un evento en Google Calendar
def eliminar_evento(event_id):
    calendar_service.events().delete(calendarId=calendar_id, eventId=event_id).execute()

@app.route('/webhook', methods=['POST'])
def webhook():
    numero = request.values.get('From', '')
    mensaje = request.values.get('Body', '').lower()
    response = 'Lo siento, no entendí tu mensaje.'

    if 'crear turno' in mensaje:
        start_time = (datetime.datetime.now() + datetime.timedelta(days=1)).isoformat()
        end_time = (datetime.datetime.now() + datetime.timedelta(days=1, hours=1)).isoformat()
        event_id = crear_evento('Turno resguarda', 'Consulta con el doctor.', start_time, end_time, numero)
        botones = [
            'Ver detalles del turno',
            f'whatsapp://send?text=aceptar%20{event_id}',
            f'whatsapp://send?text=cambiar%20{event_id}',
            f'whatsapp://send?text=cancelar%20{event_id}'
        ]
        response = f'Tu turno ha sido creado. ID del evento: {event_id}.'
        enviar_mensaje_con_botones(numero, response, botones)

    elif 'aceptar' in mensaje:
        event_id = mensaje.split()[1]
        actualizar_evento(event_id, 'aceptado')
        response = f'Tu turno {event_id} ha sido aceptado.'
        enviar_mensaje_con_botones(numero, response, [])

    elif 'cambiar' in mensaje:
        event_id = mensaje.split()[1]
        start_time = (datetime.datetime.now() + datetime.timedelta(days=2)).isoformat()
        end_time = (datetime.datetime.now() + datetime.timedelta(days=2, hours=1)).isoformat()
        actualizar_evento(event_id, 'cambiado')
        response = f'Tu turno {event_id} ha sido cambiado. Nueva fecha: {start_time}.'
        enviar_mensaje_con_botones(numero, response, [])

    elif 'cancelar' in mensaje:
        event_id = mensaje.split()[1]
        eliminar_evento(event_id)
        response = f'Tu turno {event_id} ha sido cancelado.'
        enviar_mensaje_con_botones(numero, response, [])

    return '', 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
