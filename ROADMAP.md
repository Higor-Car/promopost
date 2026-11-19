# Achou Promo — Roadmap

Plataforma de promoções para os consumidores de Maurilândia e Turvelândia.
Os comércios parceiros pagam uma mensalidade e os consumidores acessam a vitrine de graça.
Os dados são cadastrados pelo administrador (via admin do Django).

## Meta inicial
Fechar cerca de 10 comércios antes do lançamento público.

## Fase 1 — Vitrine pública
- [x] Página inicial com as promoções ativas
- [x] Filtro por cidade e categoria
- [x] Página de cada comércio, com botão de WhatsApp
- [x] Layout pensado para celular primeiro

## Fase 2 — Ajustes nos models
- [x] Validade da promoção (some da vitrine quando vence)
- [x] Categoria e cidade
- [x] Destaque de promoção
- [x] Editar e excluir promoção pelo admin

## Fase 3 — No ar
- [x] README
- [ ] Domínio (achoupromos.com.br — o achoupromo.com.br já tinha dono)
- [x] Deploy (AWS Lightsail)
- [x] QR codes para colar nos comércios parceiros

## Fase 4 — Métricas para os comércios
- [x] Contagem de visualizações e cliques por promoção e por comércio
- [x] Resumo simples para o dono do comércio ver o resultado

## Fase 5 — Instagram (@achoupromo)
- [x] Gerar a imagem "Promoções do dia" a partir da plataforma
- [x] Avaliar publicação automática via API da Meta (docs/instagram-api-meta.md)

## Extras já feitos
- [x] Busca, página própria de cada promoção, compartilhar e "Como chegar"
- [x] Novo visual (logo, ícone do site, categorias com ícone, selo de desconto)
- [x] Botão "Quero anunciar" no rodapé (WhatsApp de quem vende os anúncios)
- [x] Menu de abas no celular; páginas Lojas, Categorias e Para lojistas
- [x] Página de cada loja como mini-site (capa, horário, abas Promoções/Informações)
- [x] Ilustrações próprias e animações leves

## Divulgação (fora do código)
- Cada comércio parceiro divulga no próprio perfil e no balcão
- QR code nas lojas
- Link da plataforma em grupos de WhatsApp da cidade
- Perfil no Instagram com conteúdo diário
