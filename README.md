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
   cliente der o ok. O sistema já agenda uma postagem no Instagram e outra no
   Facebook para o horário de início (ou para agora, se o início já passou).
   Promoção que já terminou não pode ser aprovada.
4. **Postar** — abra o **Calendário**. No horário, a postagem aparece em
   **Hora de postar**: baixe a imagem, copie a legenda, poste na rede indicada
   e clique em **Marcar como publicada**. Quando Instagram e Facebook estiverem
   marcados, a promoção vira *Publicada*. (Na Fase 4 isso será automático pela
   API da Meta.)
5. **Editar** — disponível até alguma postagem ser publicada. Se você alterar
   uma promoção aprovada/agendada, o agendamento é cancelado e ela volta para
   rascunho, precisando ser aprovada de novo.
6. **Excluir** — pede confirmação e apaga a promoção junto com a imagem.
   Depois que algo foi publicado não dá mais para excluir (fica no histórico).

### Calendário

Em **Calendário** ficam as postagens do mês, dia a dia, com o status de cada
uma (Agendada, Hora de postar, Publicada ou Não publicada). Use as setas para
trocar de mês.

### Status de uma promoção

| Status | Significado |
| --- | --- |
| Rascunho | Cadastrada, ainda não revisada |
| Aguardando aprovação do cliente | Enviada para o cliente conferir |
| Aprovada | Cliente aprovou (passa para Agendada na hora) |
| Agendada | Postagens criadas para Instagram e Facebook |
| Publicada | Foi ao ar nas duas redes |
| Encerrada | Passou da data de fim (encerrada pelo agendador) |

## Agendador

O comando abaixo encerra as promoções que passaram do fim, agenda as que
foram aprovadas pelo Admin e mostra quantas postagens estão na hora de
publicar. Ele precisa rodar sozinho de tempos em tempos (recomendado: a cada
5 minutos).

```bash
python manage.py processar_agendamentos
```

Para deixar rodando numa janela do terminal, repetindo a cada 5 minutos
(feche com Ctrl+C):

```bash
python manage.py processar_agendamentos --a-cada 5
```

**Windows (Agendador de Tarefas)** — cria uma tarefa que roda a cada 5 minutos
(ajuste o caminho da pasta do projeto):

```bash
schtasks /Create /SC MINUTE /MO 5 /TN "PromoPost agendador" /TR "C:\caminho\promopost\venv\Scripts\python.exe C:\caminho\promopost\manage.py processar_agendamentos"
```

**Linux (cron)** — adicione com `crontab -e`:

```
*/5 * * * * cd /caminho/promopost && venv/bin/python manage.py processar_agendamentos >> agendador.log 2>&1
```

## Testes

```bash
python manage.py test posts
```

## Estrutura

- `config/` — configurações do Django (idioma pt-BR, fuso de São Paulo, login)
- `posts/` — app principal: models `Comercio`, `Promocao` e `Postagem`,
  telas de lista, formulário, aprovação, edição, exclusão e calendário
- `posts/agendamento.py` — regras de agendamento, publicação e encerramento
- `posts/management/commands/processar_agendamentos.py` — o agendador
- `media/` — imagens enviadas (não vai para o Git)
- `db.sqlite3` — banco de dados local (não vai para o Git)
