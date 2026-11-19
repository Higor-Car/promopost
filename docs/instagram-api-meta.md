# Publicação automática no Instagram (API da Meta) — avaliação

Data: novembro de 2026. As regras da Meta mudam com frequência; confira a
documentação oficial (developers.facebook.com, "Instagram Platform" / "Content
Publishing") antes de começar.

## Resumo

**Recomendação: por enquanto, postar à mão** a imagem gerada no Admin
(Promoções → *Imagem do dia*). Leva 1 minuto por dia e não depende de
aprovação da Meta. Vale automatizar quando o perfil @achoupromo estiver ativo
e com rotina diária, se a postagem manual virar um peso.

## O que a automação exige

1. **Conta profissional no Instagram** (Comercial ou Criador de conteúdo)
   para o @achoupromo, ligada a uma **Página do Facebook**.
2. **App na Meta for Developers**, com o produto de Instagram e a permissão de
   publicação de conteúdo (hoje chamada `instagram_content_publish`, junto com
   as permissões básicas da conta).
3. **Revisão do app pela Meta (App Review)** para usar em produção: pede
   política de privacidade publicada, descrição do uso e vídeo mostrando o
   fluxo. Costuma levar dias ou semanas e pode ser recusada na primeira vez.
4. **Verificação da empresa** (Business Verification) pode ser exigida, com
   documentos (CNPJ ou equivalente).
5. **Token de acesso de longa duração**, renovado periodicamente, guardado no
   servidor (`.env`), nunca no código.

## Como funcionaria no Achou Promo

- A imagem já é gerada pelo sistema (`posts/instagram.py`). A API não recebe
  o arquivo direto: ela baixa a imagem de um **endereço público em HTTPS**,
  então o site precisa estar com o domínio e o HTTPS ligados.
- Fluxo da API: criar um "contêiner" de mídia com a URL da imagem e a legenda
  → (para carrossel, um contêiner por imagem + um contêiner de carrossel) →
  publicar o contêiner.
- Um comando agendado no servidor (cron, como o backup) publicaria todo dia
  num horário fixo, por exemplo às 8h.
- Há limite de publicações por conta a cada 24 horas (algumas dezenas), longe
  do que o Achou Promo precisa.

## Riscos e custos

- **Sem custo em dinheiro** para usar a API; o custo é o tempo de cadastro,
  revisão e manutenção (tokens que vencem, mudanças de regra da Meta).
- Se a Meta mudar a API ou o token vencer, a postagem para sem aviso. É
  preciso monitorar (por exemplo, um e-mail ou alerta quando falhar).
- Contas novas que postam por API logo no início podem ter alcance menor;
  postar à mão nas primeiras semanas também ajuda a "aquecer" o perfil.

## Próximos passos, se decidir automatizar

1. Criar o @achoupromo como conta profissional e ligar a uma Página do Facebook.
2. Publicar a política de privacidade no site (uma página simples).
3. Criar o app na Meta for Developers e pedir a permissão de publicação.
4. Depois da aprovação, implementar o comando `publicar_instagram` usando as
   imagens que o sistema já gera.
