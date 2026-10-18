FROM python:3.11-slim

# Evita criação de arquivos .pyc e força saída direta de logs no console
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=5000

WORKDIR /app

# Instala dependências de compilação mínimas
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copia apenas o requirements primeiro para otimizar o cache de camadas do Docker
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copia o restante do código da aplicação
COPY . /app/

# Expõe a porta interna da aplicação
EXPOSE 5000

# Healthcheck embutido usando a biblioteca padrão do Python
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/')" || exit 1

# Inicializa via Gunicorn (servidor WSGI profissional para produção)
CMD ["gunicorn", "--workers", "2", "--bind", "0.0.0.0:5000", "--timeout", "120", "web_app:app"]
