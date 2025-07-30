import os
import ast
import openai
import pandas as pd
import sys
import tiktoken
from scipy import spatial
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.conf import settings
from profiles.models import Profile, Company, CustomUser
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout

# Create your views here.

# API key
openai.organization = os.getenv('OPENAI_ORG')
openai.api_key = os.getenv('OPENAI_API_KEY')

##########################################
# search_ask.py
##########################################
GPT_MODEL = "gpt-3.5-turbo-0125"
EMBEDDING_MODEL = "text-embedding-ada-002"


def num_tokens(text: str, model: str = GPT_MODEL) -> int:
    """Return the number of tokens in a string."""
    encoding = tiktoken.encoding_for_model(model)
    return len(encoding.encode(text))


# CAMBIO 1: Usar datos MIA en lugar de sercotec
try:
    df = pd.read_csv("./plataforma/mia_data/mia_embeddings.csv")
    print("✅ Cargados datos MIA UC")
except FileNotFoundError:
    # Fallback a datos originales si no existen los de MIA
    df = pd.read_csv("./plataforma/bases_sercotec_embeddings.csv")
    print("⚠️ Usando datos sercotec (MIA no encontrado)")

# convert embeddings from CSV str type back to list type
df['embedding'] = df['embedding'].apply(ast.literal_eval)


# search function
def strings_ranked_by_relatedness(
        query: str,
        df: pd.DataFrame,
        relatedness_fn=lambda x, y: 1 - spatial.distance.cosine(x, y),
        top_n: int = 100
) -> tuple[list[str], list[float]]:
    """Returns a list of strings and relatednesses, sorted from most related to least."""
    query_embedding_response = openai.Embedding.create(
        model=EMBEDDING_MODEL,
        input=query,
    )
    query_embedding = query_embedding_response["data"][0]["embedding"]
    strings_and_relatednesses = [
        (row["text"], relatedness_fn(query_embedding, row["embedding"]))
        for i, row in df.iterrows()
    ]
    strings_and_relatednesses.sort(key=lambda x: x[1], reverse=True)
    strings, relatednesses = zip(*strings_and_relatednesses)
    return strings[:top_n], relatednesses[:top_n]


def query_message(
        query: str,
        df: pd.DataFrame,
        model: str,
        token_budget: int
) -> str:
    """Return a message for GPT, with relevant source texts pulled from a dataframe."""
    strings, relatednesses = strings_ranked_by_relatedness(query, df)
    # CAMBIO 2: Mensaje adaptado para MIA UC
    introduction = 'Usa la siguiente información del catálogo de cursos del Magíster en Inteligencia Artificial (MIA) de la Universidad Católica para responder la pregunta. Si la respuesta no se encuentra en la información, escribe "No pude encontrar una respuesta."'
    question = f"\n\nPregunta: {query}"
    message = introduction
    for string in strings:
        next_article = f'\n\nInformación del curso:\n"""\n{string}\n"""'
        if (
                num_tokens(message + next_article + question, model=model)
                > token_budget
        ):
            break
        else:
            message += next_article
    return message + question


def format_response(response_text: str) -> str:
    """
    Formatea la respuesta del modelo para mejor presentación.
    Agrega estructura y organización al texto.
    """
    if not response_text:
        return response_text

    # Limpiar el texto
    text = response_text.strip()

    # Dividir en párrafos usando puntos seguidos de espacios
    paragraphs = []
    current_paragraph = ""

    sentences = text.split('. ')

    for i, sentence in enumerate(sentences):
        sentence = sentence.strip()
        if not sentence:
            continue

        # Agregar el punto al final si no es la última oración
        if i < len(sentences) - 1 and not sentence.endswith('.'):
            sentence += '.'

        current_paragraph += sentence + " "

        # Crear nuevo párrafo cada 2-3 oraciones o cuando detectemos temas nuevos
        if (len(current_paragraph.split('. ')) >= 3 or
                any(keyword in sentence.lower() for keyword in
                    ['además', 'por otro lado', 'también', 'asimismo', 'finalmente'])):
            paragraphs.append(current_paragraph.strip())
            current_paragraph = ""

    # Agregar el último párrafo si existe
    if current_paragraph.strip():
        paragraphs.append(current_paragraph.strip())

    # Detectar y formatear listas
    formatted_paragraphs = []
    for paragraph in paragraphs:
        # Detectar patrones de lista
        if re.search(r'\d+\.\s', paragraph) or re.search(r'[-•]\s', paragraph):
            # Es una lista, mantener formato
            formatted_paragraphs.append(paragraph)
        elif ':' in paragraph and len(paragraph.split(':')) == 2:
            # Podría ser título: descripción
            parts = paragraph.split(':', 1)
            formatted_paragraphs.append(f"**{parts[0].strip()}:**\n{parts[1].strip()}")
        else:
            formatted_paragraphs.append(paragraph)

    # Unir párrafos con doble salto de línea
    formatted_text = '\n\n'.join(formatted_paragraphs)

    return formatted_text


def ask(
        query: str,
        df: pd.DataFrame = df,
        model: str = GPT_MODEL,
        token_budget: int = 4096 - 500,
        print_message: bool = False,
        profile: Profile = None,
) -> str:
    """Answers a query using GPT and a dataframe of relevant texts and embeddings."""
    message = query_message(query, df, model=model, token_budget=token_budget)
    if print_message:
        print(message)

    # CAMBIO 3: Mensaje de sistema mejorado para respuestas estructuradas
    system_message = """Eres un asistente del catálogo de cursos UC. Ayudas con información sobre cursos, créditos, contenidos y bibliografía.

IMPORTANTE: Estructura tus respuestas de manera clara y organizada:
- Usa párrafos separados para diferentes temas
- Organiza la información de manera lógica
- Si mencionas múltiples cursos o elementos, preséntalos de forma ordenada
- Usa un lenguaje claro y profesional
- Separa las ideas principales en párrafos distintos"""

    if profile is not None:
        system_message += f" Saluda a {profile.name} por su nombre."

    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": message},
    ]

    response = openai.ChatCompletion.create(
        model=model,
        messages=messages,
        temperature=0.7  # Reducido para respuestas más consistentes
    )

    response_message = response["choices"][0]["message"]["content"]

    # Formatear la respuesta antes de devolverla
    formatted_response = format_response(response_message)

    return formatted_response


##########################################

def index(request):
    if request.method == 'POST':
        tematica = request.POST.get('tematica')
        nivel = request.POST.get('nivel')

        if 'action' in request.POST and request.POST.get('action') == 'estrategias':
            prompt = generate_strategies_prompt(tematica, nivel)
        else:
            prompt = generate_about_topic_prompt(tematica, nivel)

        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=prompt,
            max_tokens=500,
            n=1,
            stop=None,
            temperature=0)
        output = response.choices[0].text.strip()
        request.session['output'] = output

        return render(request, 'index.html', {'tematica': tematica, 'output': request.session.get('output')})

    return render(request, 'index.html')


@csrf_exempt
def capital_semilla_chat(request, *args, **kwargs):
    if request.method == 'POST':
        user = request.user
        if user.is_authenticated:
            query = request.POST.get('query')
            historic_questions = request.POST.get('historic_questions')
            historic_answers = request.POST.get('historic_answers')
            profile = Profile.objects.filter(user=request.user).first()

            # Determinar el nombre del usuario
            if profile and profile.name:
                user_name = profile.name
            else:
                user_name = user.username

            # Si es una petición especial para obtener solo el nombre
            if query == "init":
                return JsonResponse({
                    'response': '',
                    'user_name': user_name,
                    'init': True
                })

            # Procesar pregunta normal
            if profile is not None:
                response = ask(query, profile=profile)
            else:
                response = ask(query)

            return JsonResponse({
                'response': response,
                'user_name': user_name
            })
        else:
            return JsonResponse({
                'response': "Usuario no autenticado. Por favor, inicia sesión para continuar.",
                'user_name': 'Usuario'
            })

    # Para GET request
    return render(request, 'capital_semilla_chat.html')


def generate_strategies_prompt(tematica, nivel):
    levels = {
        'estoy_aprendiendo': 'Estoy aprendiendo',
        'he_escuchado': 'He escuchado del tema',
        'lo_conozco': 'Lo conozco',
        'lo_utilizo': 'Lo conoce y lo utiliza',
        'Conozco_acabadamente_sobre_el_tema': 'Conoce acabadamente sobre el tema',
    }

    return f"""Proporciona estrategias de aprendizaje para {tematica}, dirigidas a alguien con nivel '{levels[nivel]}'. 

Estructura tu respuesta en párrafos claros, organizando la información de manera lógica y fácil de seguir. Máximo 400 palabras."""


def generate_about_topic_prompt(tematica, nivel):
    levels = {
        'estoy_aprendiendo': 'Estoy aprendiendo',
        'he_escuchado': 'He escuchado del tema',
        'lo_conozco': 'Lo conozco',
        'lo_utilizo': 'Lo conoce y lo utiliza',
        'Conozco_acabadamente_sobre_el_tema': 'Conoce acabadamente sobre el tema',
    }

    return f"""Explica los conceptos clave sobre {tematica} para alguien con nivel '{levels[nivel]}'. 

Organiza tu respuesta en párrafos claros:
- Conceptos fundamentales
- Elementos centrales
- Elementos secundarios
- Temas relacionados para profundizar

Máximo 400 palabras, con estructura clara y fácil de leer."""


def semilla(request, *args, **kwargs):
    return render(request, 'capital_semilla_chat.html', {})