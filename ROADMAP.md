# Roadmap - PromoPost

Sistema para agendar e publicar promoções de comércios de Maurilândia e Turvelândia no Instagram e no Facebook.

## Fase 1 - MVP (painel)
- [x] Projeto Django com app `posts`
- [x] Models: Comercio, Promocao, Postagem
- [x] Admin para cadastrar comércios e promoções
- [x] Tela de listagem e formulário de upload de promoção
- [x] Validação: fim da promoção depois do início
- [x] Testes de criação e validação
- [ ] Login (telas hoje estão abertas)
- [ ] Botão de aprovar promoção (rascunho -> aprovada)
- [ ] Editar e excluir promoção
- [ ] README com instruções de uso

## Fase 2 - Agendador
- [ ] Job que cria as `Postagem` quando a promoção é aprovada
- [ ] Tarefa periódica (cron ou Celery) que muda o status no horário certo
- [ ] Encerrar a promoção automaticamente no fim da data
- [ ] Tela de calendário de postagens

## Fase 3 - Legenda com IA
- [ ] Gerar legenda sugerida com a API do Claude a partir do título e do comércio
- [ ] Revisão manual da legenda antes de aprovar

## Fase 4 - Publicação automática (Meta)
- [ ] Criar app na Meta e pedir revisão cedo (demora)
- [ ] Política de privacidade e vídeo de demonstração para a revisão
- [ ] Autorização das páginas dos clientes (sem pedir senha)
- [ ] Publicação no Instagram e no Facebook pela API oficial
- [ ] Registro de erros por postagem

## Fase 5 - Entrada pelo WhatsApp (futuro)
- [ ] Receber foto e dados da promoção pelo WhatsApp Business API
- [ ] Aprovação do cliente por mensagem

## Negócio (fora do código)
- [ ] Piloto com 5 a 10 comércios
- [ ] Tabela de pacotes (básico, semanal, diário)
- [ ] Roteiro de visita para apresentar o serviço
