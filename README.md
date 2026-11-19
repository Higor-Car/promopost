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
2. **Comércios** — nome, categoria, cidade, logo, **foto de capa**
   (horizontal, opcional; sem ela a loja ganha uma capa colorida desenhada),
   descrição, **horário de funcionamento** (uma linha por dia ou faixa),
   endereço, WhatsApp (com DDD, de qualquer jeito: `(64) 99999-1234`
   funciona) e Instagram. O **slug** é o endereço da página do comércio
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

No celular, um **menu de abas embaixo da tela** (Promoções, Lojas,
Categorias, Anunciar), como um aplicativo; no computador, o menu fica no topo.

- **Página inicial** — chamada curta ("As promoções de Maurilândia e
  Turvelândia em um só lugar"), filtro por **cidade** e pelas 6 **categorias**
  com mais ofertas, "Em destaque", "Acaba hoje", **lojas parceiras**, as
  demais promoções e um chamado discreto para lojistas. Trocar de cidade ou
  categoria **não recarrega a página** (o conteúdo troca suavemente e o botão
  "voltar" funciona). **Busca** (acha "acougue" em "Açougue", busca no título,
  descrição, loja e categoria). Selos de **desconto** (ex.: -17%) e "Acaba hoje".
- **Lojas** (`/lojas/`) — todas as lojas parceiras com capa, logo e quantas
  ofertas têm no ar, com filtro por cidade e categoria.
- **Categorias** (`/categorias/`) — lista das categorias que têm loja ou
  oferta (as vazias não aparecem).
- **Para lojistas** (`/para-lojistas/`) — página curta para os comércios: 3
  vantagens, como funciona em 3 passos e 3 dúvidas comuns. Os números reais do
  site (lojas, visitas, chamadas) aparecem sozinhos quando passarem de 5 lojas
  e 300 visitas em 30 dias.
- **Página da promoção** (`/p/<número>/`) — foto grande, preço, economia,
  validade, botão **Quero essa promoção** (abre o WhatsApp da loja com a
  mensagem pronta), **Compartilhar**, **Como chegar** e outras promoções da
  mesma loja. Promoção vencida mostra um aviso e as que ainda valem.
- **Página do comércio** (`/c/<slug>/`) — um mini-site da loja: capa, logo,
  botões **Chamar no WhatsApp**, **Como chegar** (Google Maps),
  **Instagram** e **Compartilhar**, e duas abas: **Promoções** e
  **Informações** (sobre, horário, endereço e contato).
- Visual limpo, sem emojis: ícones de traço fino desenhados no padrão do
  site e uma ilustração própria (SVG) só na chamada do computador. As
  animações são curtas e discretas e desligam sozinhas para quem ativou
  "reduzir movimento" no celular.
- Os links ficam com título e foto quando compartilhados no WhatsApp.
- Rodapé com **"Quero anunciar"** (abre o WhatsApp de quem vende os
  anúncios) quando `ACHOUPROMO_CONTATO_WHATSAPP` está preenchido no `.env`.

## Resultado para o dono da loja

Cada comércio tem um **link privado de resultado** (sem senha), que aparece
na ficha do comércio no Admin, em *Resultado para o dono da loja*, e na
coluna **resultado** da lista. Mande o link para o dono pelo WhatsApp.

A página mostra, em 7, 30 ou 90 dias:

- chamadas no WhatsApp, visitas, vezes que as promoções apareceram e acessos
  pelo QR code da loja;
- gráfico de visitas por dia e cliques em "Como chegar" e no Instagram;
- números de cada promoção.

Não contam robôs, prévias de link (WhatsApp, Facebook) nem quem está logado
no Admin. O site guarda só contadores por dia, sem IP nem dados de quem
acessou. Se um link vazar, use a ação **"Gerar novo link de resultado"** na
lista de comércios: o antigo para de funcionar.

## Instagram: imagem do dia

Em **Promoções**, botão **📸 Imagem do dia (Instagram)**: gera imagens
1080×1350 (formato do feed) com até 6 promoções, 3 por imagem; com mais de
3, poste como carrossel. Sem escolher nada entram os destaques e as que
acabam antes. Para escolher, marque na lista e use a ação **"Gerar imagem do
Instagram com as selecionadas"**.

A avaliação da publicação automática pela API da Meta está em
[docs/instagram-api-meta.md](docs/instagram-api-meta.md).

## QR codes para as lojas

No Admin, em **Comércios**, selecione as lojas e escolha a ação **"Imprimir
QR codes"**. Abre uma página com um cartão por loja (2 por folha A4) com o
QR code da página da loja no site. É só imprimir e recortar. Os acessos
pelo QR code aparecem no resultado da loja.

## Site no ar (AWS Lightsail)

O site roda num servidor **AWS Lightsail** (Ubuntu 24.04, região São Paulo)
com nginx + gunicorn. O banco (SQLite) e as fotos ficam no disco do servidor,
em `/srv/achoupromo/`. Os arquivos do servidor estão na pasta `deploy/`.

Segurança do servidor:

- No firewall do Lightsail só ficam abertas as portas 80 e 443 (o site). A
  porta 22 (SSH) aceita apenas o botão **Connect using SSH** do console.
- O site roda com um usuário próprio e só consegue escrever no banco e nas
  fotos. O nginx não tem acesso ao banco nem ao `.env` (chave secreta).
- O login do admin aceita no máximo 10 tentativas por minuto por IP.
- As atualizações de segurança do Ubuntu são instaladas sozinhas.

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

O domínio do site é **achoupromos.com.br** (o `achoupromo.com.br`, sem "s",
já tinha dono). Ele fica configurado em um só lugar: o `SITE_URL` do `.env`
do servidor.

1. Registre o domínio no [Registro.br](https://registro.br).
2. No Registro.br, em **DNS → Editar zona**, crie dois registros do tipo
   **A**: um com o nome em branco (o próprio domínio) e outro com o nome
   `www`, os dois apontando para o **IP fixo** do servidor (aparece no
   console do Lightsail).
3. Quando o endereço já abrir o site (pode levar algumas horas), instale o
   certificado HTTPS, grátis e renovado sozinho:

```bash
sudo bash /srv/achoupromo/app/deploy/https.sh seu-email@exemplo.com
```

Para trocar de domínio no futuro (ex.: se conseguir um nome melhor), rode o
comando abaixo, aponte o DNS do domínio novo e rode o `https.sh` de novo:

```bash
sudo bash /srv/achoupromo/app/deploy/trocar-dominio.sh novodominio.com.br
```

### Instalar do zero (servidor novo)

Num Ubuntu 24.04 novo, com as portas 80 e 443 liberadas (e a 22 restrita ao SSH do console):

```bash
curl -fsSL https://raw.githubusercontent.com/Higor-Car/promopost/main/deploy/instalar.sh -o instalar.sh
```

```bash
sudo bash instalar.sh IP_DO_SERVIDOR achoupromos.com.br
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
