# PromoPost

Painel para cadastrar, aprovar e (em breve) agendar promoções de comércios de
Maurilândia e Turvelândia para publicar no Instagram e no Facebook.

O que falta fazer está no [ROADMAP.md](ROADMAP.md).

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

Instale as dependências, crie o banco e o usuário de acesso:

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
```

## Rodando o sistema

Com o ambiente virtual ativado:

```bash
python manage.py runserver
```

Abra <http://127.0.0.1:8000/> no navegador e entre com o usuário criado acima.

## Como usar

1. **Cadastrar comércios** — em **Admin** (<http://127.0.0.1:8000/admin/>), em
   *Comércios*, cadastre nome, cidade, WhatsApp, Instagram, plano e mensalidade.
2. **Cadastrar uma promoção** — em **Nova promoção**, escolha o comércio,
   preencha título, legenda, imagem e as datas de início e fim.
   O fim precisa ser depois do início.
3. **Aprovar** — na lista de **Promoções**, clique em **Aprovar** quando o
   cliente der o ok. Só promoções em rascunho ou aguardando aprovação podem
   ser aprovadas.
4. **Editar** — disponível enquanto a promoção está em rascunho, aguardando ou
   aprovada. Se você alterar uma promoção já aprovada, ela volta para
   rascunho e precisa ser aprovada de novo.
5. **Excluir** — pede confirmação e apaga a promoção junto com a imagem.
   Promoções já publicadas não podem ser excluídas (ficam como histórico).

### Status de uma promoção

| Status | Significado |
| --- | --- |
| Rascunho | Cadastrada, ainda não revisada |
| Aguardando aprovação do cliente | Enviada para o cliente conferir |
| Aprovada | Cliente aprovou, pronta para agendar |
| Agendada | Postagens criadas para Instagram/Facebook |
| Publicada | Já foi ao ar |
| Encerrada | Passou da data de fim |

## Testes

```bash
python manage.py test posts
```

## Estrutura

- `config/` — configurações do Django (idioma pt-BR, fuso de São Paulo, login)
- `posts/` — app principal: models `Comercio`, `Promocao` e `Postagem`,
  telas de lista, formulário, aprovação, edição e exclusão
- `media/` — imagens enviadas (não vai para o Git)
- `db.sqlite3` — banco de dados local (não vai para o Git)
