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
GPT_MODEL = "gpt-4"
EMBEDDING_MODEL = "text-embedding-ada-002"

def num_tokens(text: str, model: str = GPT_MODEL) -> int:
    """Return the number of tokens in a string."""
    encoding = tiktoken.encoding_for_model(model)
    return len(encoding.encode(text))

df = pd.read_csv("./plataforma/bases_sercotec_embeddings.csv")

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
    introduction = 'Usa los siguientes artículos sobre la base de datos para responder la siguiente pregunta. Si la respuesta no se encuentra en los artículos, escribe "No pude encontrar una respuesta."'
    question = f"\n\nPregunta: {query}"
    message = introduction
    for string in strings:
        next_article = f'\n\nSección del Manual:\n"""\n{string}\n"""'
        if (
            num_tokens(message + next_article + question, model=model)
            > token_budget
        ):
            break
        else:
            message += next_article
    return message + question

def ask(
    query: str,
    df: pd.DataFrame = df,
    model: str = GPT_MODEL,
    token_budget: int = 4096 - 500,
    print_message: bool = False,
    profile: Profile = None,  # Nuevo parámetro
) -> str:
    """Answers a query using GPT and a dataframe of relevant texts and embeddings."""
    message = query_message(query, df, model=model, token_budget=token_budget)
    if print_message:
        print(message)
    # Personaliza el mensaje de sistema con el nombre del perfil
    system_message = f"Saluda a {profile.name} por su nombre."
    if profile is not None:
        system_message += f" Saluda a {profile.name} por su nombre."
    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": message},
    ]
    response = openai.ChatCompletion.create(
        model=model,
        messages=messages,
        temperature=0.8
    )
    response_message = response["choices"][0]["message"]["content"]
    return response_message

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

            if profile is not None:
                response = ask(query, profile=profile)
            else:
                response = "No profile found for this user."

            return JsonResponse({'response': response})
        else:
            return JsonResponse({'response': "User not logged in."})

    return render(request, 'capital_semilla_chat.html')



def generate_strategies_prompt(tematica, nivel):
    levels = {
        'estoy_aprendiendo': 'Estoy aprendiendo',
        'he_escuchado': 'He escuchado del tema',
        'lo_conozco': 'Lo conozco',
        'lo_utilizo': 'Lo conoce y lo utiliza',
        'Conozco_acabadamente_sobre_el_tema': 'Conoce acabadamente sobre el tema',
    }
    
    return f"En no más de 400 palabras, estas son algunas estrategias para aprender sobre {tematica}. Para alguien con el nivel de autoeficiencia '{levels[nivel]}', resaltando aspectos claves. "

def generate_about_topic_prompt(tematica, nivel):
    levels = {
        'estoy_aprendiendo': 'Estoy aprendiendo',
        'he_escuchado': 'He escuchado del tema',
        'lo_conozco': 'Lo conozco',
        'lo_utilizo': 'Lo conoce y lo utiliza',
        'Conozco_acabadamente_sobre_el_tema': 'Conoce acabadamente sobre el tema',
    }

    return f"""En no más de 400 palabras, estas son algunas nociones claves sobre {tematica}. Para alguien con el nivel de autoeficiencia '{levels[nivel]}'. Además, estos son algunos otros temas de interés para cuando se profundice más aún sobre {tematica}.
                - Señalando elementos centrales
                    - Elementos secundarios
    """


def semilla(request, *args, **kwargs):
    return render(request, 'capital_semilla_chat.html', {})