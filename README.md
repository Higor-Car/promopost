# Achou Promo

Vitrine de promoções dos comércios de **Maurilândia e Turvelândia**.
Os comércios parceiros pagam uma mensalidade, e os consumidores veem as
promoções de graça, sem precisar de login. Quem cadastra tudo é o
administrador, pelo Admin do Django.

O que falta fazer está no [ROADMAP.md](ROADMAP.md). A versão antiga do
projeto (PromoPost, com agendamento de postagens) está guardada na tag
`promopost-v1` do Git.

## Requisitos

- Python 3.12 ou mais novo
- Git

## Instalação (primeira vez)

No terminal, dentro da pasta do projeto:

```bash
python -m venv venv
```

Ative o ambiente virtual:

- Windows (PowerShell): `venv\Scripts\Activate.ps1`
- Linux/macOS: `source venv/bin/activate`

Instale as dependências, crie o banco e o usuário administrador:

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
```

## Rodando

```bash
python manage.py runserver
```

- Vitrine (público): <http://127.0.0.1:8000/>
- Admin (cadastros): <http://127.0.0.1:8000/admin/>

## Como cadastrar

Tudo é feito no **Admin**.

1. **Categorias** — já vêm 11 prontas (Mercado, Açougue, Padaria,
   Farmácia, Restaurante e lanchonete, Roupas e calçados, Beleza, Casa e
   construção, Pet, Serviços, Outros). Dá para criar outras e mudar a
   **ordem** em que aparecem.
2. **Comércios** — nome, categoria, cidade, logo, descrição, endereço,
   WhatsApp (com DDD, de qualquer jeito: `(64) 99999-1234` funciona) e
   Instagram. O **slug** é o endereço da página do comércio
   (`/c/mercado-sao-jose/`) e é preenchido sozinho a partir do nome.
   Desmarcar **ativo** tira o comércio e todas as promoções dele da vitrine.
3. **Promoções** — comércio, título, imagem (de preferência quadrada),
   descrição e, se quiser, preço e "preço antes" (aparece riscado).
   - **Aparece a partir de** e **válida até**: a promoção só aparece na
     vitrine nesse período e some sozinha quando vence.
   - **Destaque**: aparece primeiro, com selo amarelo. Dá para marcar
     direto na lista de promoções.
   - Na lista dá para filtrar por situação (*na vitrine*, *ainda vai
     entrar*, *vencida*), cidade e categoria.
   - Para tirar promoções do ar antes da hora: selecione na lista e use a
     ação **"Encerrar agora"**.
   - Editar e excluir: clique na promoção; o botão **Excluir** fica no fim
     da página.

## O que o consumidor vê

- **Página inicial** — promoções valendo agora, destaques primeiro, com
  filtro por cidade e por categoria (só aparecem as categorias que têm
  promoção no ar). Selo "Acaba hoje" no que vence no dia.
- **Página do comércio** — logo, endereço, Instagram, botão **Chamar no
  WhatsApp** e as promoções do comércio. Cada promoção tem o botão
  **Quero essa promoção**, que abre o WhatsApp do comércio com uma
  mensagem pronta citando a promoção.
- Os links ficam com título e imagem quando compartilhados no WhatsApp.

## QR codes para as lojas

No Admin, em **Comércios**, selecione as lojas e escolha a ação **"Imprimir
QR codes"**. Abre uma página com um cartão por loja (2 por folha A4) com o
QR code da página da loja no site. É só imprimir e recortar.

## Site no ar (AWS Lightsail)

O site roda num servidor **AWS Lightsail** (Ubuntu 24.04, região São Paulo)
com nginx + gunicorn. O banco (SQLite) e as fotos ficam no disco do servidor,
em `/srv/achoupromo/`. Os arquivos do servidor estão na pasta `deploy/`.

### Publicar uma versão nova

Depois de enviar as mudanças para o GitHub, entre no servidor (no console do
Lightsail, botão **Connect using SSH**) e rode:

```bash
sudo bash /srv/achoupromo/app/deploy/atualizar.sh
```

O script faz backup do banco, baixa o código, aplica as migrações e reinicia
o site.

### Outros comandos no servidor

```bash
sudo bash /srv/achoupromo/app/deploy/manage.sh createsuperuser
```

```bash
sudo journalctl -u achoupromo -n 100
```

O primeiro cria outro usuário do Admin. O segundo mostra os últimos registros
do site (útil quando algo dá erro).

### Backups

- **Banco:** cópia automática todo dia às 03:30 em `/srv/achoupromo/backups/`
  (guarda 14 dias).
- **Servidor inteiro (banco + fotos):** ative os *snapshots automáticos* da
  instância no console do Lightsail (aba **Snapshots**).

### Domínio e HTTPS

1. Registre `achoupromo.com.br` no [Registro.br](https://registro.br).
2. No Registro.br, em **DNS → Editar zona**, crie dois registros do tipo
   **A**: um para `achoupromo.com.br` e outro para `www.achoupromo.com.br`,
   os dois apontando para o **IP fixo** do servidor (aparece no console do
   Lightsail).
3. Quando o endereço já abrir o site (pode levar algumas horas), instale o
   certificado HTTPS, grátis e renovado sozinho:

```bash
sudo bash /srv/achoupromo/app/deploy/https.sh seu-email@exemplo.com
```

### Instalar do zero (servidor novo)

Num Ubuntu 24.04 novo, com as portas 80 e 443 liberadas:

```bash
curl -fsSL https://raw.githubusercontent.com/Higor-Car/promopost/main/deploy/instalar.sh -o instalar.sh
```

```bash
sudo bash instalar.sh IP_DO_SERVIDOR
```

## Testes

```bash
python manage.py test posts
```

## Estrutura

- `config/` — configurações do Django (pt-BR, fuso de São Paulo)
- `posts/` — app principal
  - `models.py` — `Categoria`, `Comercio` e `Promocao`
  - `admin.py` — telas de cadastro
  - `views.py` e `templates/vitrine/` — vitrine pública
- `media/` — imagens enviadas (não vai para o Git)
- `db.sqlite3` — banco de dados local (não vai para o Git)
