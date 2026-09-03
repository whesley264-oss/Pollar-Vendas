# 🤖 Pollar Vendas - Bot Discord

Bot oficial da **Pollar Vendas**, feito para ficar no servidor da Pollar no Discord. Ele cuida dos atendimentos com **tickets por botões**, envia **embeds**, cria **boas-vindas** e monta a estrutura automaticamente.

## ✨ Funcionalidades

- 🎫 **Central de Tickets** com botões: Compra, Venda, Suporte, Denúncia e Outro
- 🔒 **Fechamento de tickets** com log e transcrição das mensagens
- 👋 **Mensagens de boas-vindas** para novos membros
- 🛒 **Cargo automático** para novos membros (opcional
- 📢 **Comando de anúncio** com embed bonito
- ⚙️ **Auto-configuração**: cria categoria de tickets, canal de logs e canais do painel sozinho

## 🚀 Como rodar

1. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
2. Crie o arquivo `.env` a partir do exemplo e preencha o token:
   ```bash
   cp .env.example .env
   # edite o .env e cole o token do bot em DISCORD_TOKEN
   ```
3. Rode o bot:
   ```bash
   python main.py
   ```

## ☁️ Deploy na VertraCloud

1. Suba este repositório (público ou privado) para o GitHub.
2. No painel da VertraCloud, escolha **Deploy via GitHub** e selecione o repositório.

3. O entry point `main.py` é detectado automaticamente.
4. Configure a variável `DISCORD_TOKEN` nas variáveis de ambiente do projeto (o `.env` não é enviado para nuvem)。
5. O bot sobe sozinho e o comando `!setup` organiza os canais de tickets no servidor.

## 📋 Comandos

| Comando | Descrição | Permissão |
|---------|-----------|------------|
| `!setup` | Cria os painéis de tickets e boas-vindas no servidor | Equipe |
| `!anuncio #canal mensagem` | Envia um anúncio formatado num canal | Equipe |
| `!ticket` | Mostra o painel para abrir um ticket | Todos |

## 🛠️ Configuração

Edite o `.env` conforme a sua necessidade:

| Variável | O que é | Padrão |
|----------|----------|--------|
| `DISCORD_TOKEN` | Token do bot (Discord Developer Portal | — |
| `STAFF_ROLE_NAME` | Cargo que pode ver/gerenciar os tickets | `Equipe` |
| `TICKET_CATEGORY_NAME` | Categoria onde os tickets são criados | `Tickets` |
| `TICKET_LOGS_NAME` | Canal que recebe os logs dos tickets | `transcripts` |
| `WELCOME_CHANNEL_NAME` | Canal de boas-vindas | `boas-vindas` |
| `AUTO_ROLE_NAME` | Cargo dado automaticamente a novos membros (vazio = desativado | (vazio |

## 🤝 Como usar

1. Rode `!setup` no servidor (precisa do cargo **Equipe**
2. O bot cria o canal `#tickets` com o painel de botões e o canal de boas-vindas
3. Clientes clicam no botão do assunto e o bot cria um canal privado de ticket
4. Ao fechar, o ticket é deletado e um **transcript** é salvo no canal `#transcripts`

Feito com 💙 pela **Pollar Vendas**
