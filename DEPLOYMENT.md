# Guia de Deploy no Google Cloud Platform (GCP) ☁️

Como você já está usando os serviços do Google, rodar o bot no **Google Compute Engine (GCE)** é uma excelente escolha. Você pode usar o plano **Always Free** para ter um servidor rodando 24/7 sem custo.

## 1. Criando a Máquina Virtual (VM)

1. Vá para o [Console do GCP](https://console.cloud.google.com/).
2. No menu lateral, acesse **Compute Engine** > **VM Instances**.
3. Clique em **Create Instance**.
4. **Configurações cruciais para ser GRÁTIS:**
   - **Region**: Escolha `us-central1` (Iowa), `us-east1` (South Carolina) ou `us-west1` (Oregon).
   - **Machine type**: Escolha **Series E2** e o tamanho **e2-micro** (este é o único gratuito).
   - **Boot Disk**: Clique em **ALTERAR** (Change).
     - **Tipo de disco**: Selecione **Disco permanente padrão** (Standard Persistent Disk).
     - **Tamanho**: 10GB a 30GB.
5. Clique em **Create**.

---

## 2. Preparando o Servidor

Após a VM ficar pronta (bolinha verde), clique no botão **SSH** para abrir o terminal.

1. **Atualize o sistema e instale o Python:**
   ```bash
   sudo apt update
   sudo apt install python3-pip python3-venv git -y
   ```

2. **Clone seu projeto:**
   ```bash
   git clone <URL_DO_SEU_REPOSITÓRIO>
   cd TeleGrana
   ```

3. **Crie e ative o ambiente virtual:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

---

## 3. Configurando os Segredos

Como o `.env` e o `credentials.json` não estão no GitHub, você precisa criá-los manualmente no servidor:

1. **Crie o arquivo .env:**
   ```bash
   nano .env
   ```
   *Cole o conteúdo do seu .env local, salve com `Ctrl+O`, Enter e saia com `Ctrl+X`.*

2. **Crie o arquivo credentials.json:**
   ```bash
   nano credentials.json
   ```
   *Cole o conteúdo do seu JSON de credenciais, salve e saia.*

---

## 4. Rodando 24/7 (Como Serviço)

1. **Crie o arquivo de serviço:**
   ```bash
   sudo nano /etc/systemd/system/telegrana.service
   ```

2. **Cole este conteúdo (Ajuste `<SEU_USUARIO>`):**
   ```ini
   [Unit]
   Description=Bot TeleGrana
   After=network.target

   [Service]
   User=<SEU_USUARIO>
   WorkingDirectory=/home/<SEU_USUARIO>/TeleGrana
   ExecStart=/home/<SEU_USUARIO>/TeleGrana/venv/bin/python main.py
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```
   *(Substitua `<SEU_USUARIO>` pelo nome que aparece no seu terminal SSH).*

3. **Ative o bot:**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable telegrana
   sudo systemctl start telegrana
   ```

**Checar status:** `sudo systemctl status telegrana`

---

## 5. Como Atualizar o Bot (Após um Push)

Sempre que você fizer alterações no seu computador e der um `git push`, siga estes passos no terminal SSH da VM para atualizar o bot:

0. **Clique nesse site: [https://console.cloud.google.com/compute/instances](https://console.cloud.google.com/compute/instances)**

1. **Vá para a pasta do projeto:**
   ```bash
   cd TeleGrana
   ```

2. **Puxe as novidades do GitHub:**
   ```bash
   git pull
   ```

3. **Atualize as dependências (se necessário):**
   ```bash
   source venv/bin/activate
   pip install -r requirements.txt
   ```

4. **Reinicie o serviço para aplicar as mudanças:**
   ```bash
   sudo systemctl restart telegrana
   ```

**Dica:** Se você quiser ver o que o bot está fazendo em tempo real após reiniciar, use:
`sudo journalctl -u telegrana -f`
