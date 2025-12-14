FROM python:3.11-slim

# Çalışma dizinini ayarla
WORKDIR /app

# Gerekli sistem paketlerini yükle (opsiyonel, ihtiyaca göre artırılabilir)
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python bağımlılıklarını kopyala ve yükle
# .venv kullanmıyoruz, doğrudan sisteme kuruyoruz
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kaynak kodları kopyala (Dev Container modunda bu adım bind mount ile ezilir ama prod için gereklidir)
COPY . .

# Konteynerin hemen kapanmaması için (Dev modunda işe yarar)
CMD ["tail", "-f", "/dev/null"]
