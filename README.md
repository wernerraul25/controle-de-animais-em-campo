# Sistema de Contagem de Passagem IoT

Este projeto é uma solução IoT completa baseada em Raspberry Pi, desenvolvida para monitorar, contar e registrar a passagem de objetos ou animais em dois pontos independentes (A e B). O sistema fornece feedback visual local com LEDs e exibe os dados em um dashboard web em tempo real, que também permite o gerenciamento de um histórico de contagens.

**Integrantes:**
* Raul Werner - 1129436
* Marcos Bristot - 1134659
* Guilherme Henrique Baschera - 1134266

---

## 1. Visão Geral

O sistema é dividido em dois componentes principais que rodam na Raspberry Pi:

1.  **Script de Hardware (`sensor.py`):** Um script Python que lê continuamente dois sensores ultrassônicos. Ao detectar uma nova passagem, ele envia um evento para o servidor web e pisca um LED correspondente.
2.  **Aplicação Web (`app.py`):** Um servidor Flask que atua como backend e frontend. Ele recebe os eventos, armazena as contagens em um banco de dados SQLite e serve um dashboard HTML/JS para o usuário.

## 2. Funcionalidades Principais

* **Contagem em Tempo Real:** O dashboard exibe as contagens separadas para o "Ponto A", "Ponto B" e o "Total".
* **Feedback Visual Imediato:** Um LED dedicado a cada sensor (LED A, LED B) pisca brevemente no momento exato em que uma nova passagem é detectada.
* **Banco de Dados Persistente:** As contagens ao vivo são salvas em um banco de dados (SQLite), garantindo que os dados não sejam perdidos se o sistema for reiniciado.
* **Arquivamento de Sessão:** O usuário pode clicar em um botão no dashboard para "Arquivar" a sessão atual. Isso move as contagens (A, B, Total) para uma tabela de "Histórico" e zera os contadores ao vivo.
* **Gerenciamento do Histórico:** No mesmo dashboard, o usuário pode ver uma tabela de todas as sessões arquivadas. Ele pode:
    * **Excluir** sessões de contagem antigas.
    * **Adicionar/Editar anotações** (ex: "Contagem da manhã") para cada sessão salva.
* **Correção de Fuso Horário:** O servidor é configurado para o fuso `America/Sao_Paulo`, garantindo que os timestamps no histórico estejam corretos.

## 3. Hardware e Conexões (Pinos BCM)

| Componente | Conexão na Raspberry Pi |
| :--- | :--- |
| **Sensor A** (HC-SR04) | `TRIG`: GPIO 18, `ECHO`: GPIO 24 |
| **Sensor B** (HC-SR04) | `TRIG`: GPIO 17, `ECHO`: GPIO 27 |
| **LED A** | `Sinal`: GPIO 22 |
| **LED B** | `Sinal`: GPIO 23 |
| (Sensores e LEDs) | `VCC` em 5V, `GND` em GND |

## 4. Arquitetura do Software

O software é composto por 3 partes principais que rodam na Pi.

/projeto\_contagem/
│
├── app.py              \# Servidor Flask (Backend API + Frontend)
├── sensor.py           \# Script dos Sensores e LEDs (Hardware)
├── init\_db.py          \# Script para criar o banco de dados (rodar 1 vez)
├── monitoramento.db    \# Banco de dados SQLite (criado pelo init\_db)
│
└── /templates/
└── index.html      \# O Dashboard web (HTML/JS/CSS)


### `sensor.py` (O Detector)
* Usa `RPi.GPIO` para ler os sensores A e B.
* Utiliza uma lógica de **"borda de subida"** (rising-edge): ele só conta quando o sensor *muda* de "livre" para "ocupado", evitando múltiplas contagens para um objeto parado.
* Ao detectar uma passagem, pisca o LED correspondente (ex: `PIN_LED_A`) por 0.3 segundos.
* Envia uma requisição `POST` para o `app.py` (em `http://127.0.0.1:5000/api/evento`) com o sensor que foi disparado (ex: `{"sensor": "A"}`).

### `app.py` (O Cérebro)
* Servidor web **Flask** que gerencia os dados.
* `GET /`: Serve o `index.html` (o dashboard).
* `GET /api/status`: Envia os dados ao vivo e o histórico (em formato JSON) para o dashboard.
* `POST /api/evento`: Recebe o evento do `sensor.py` e incrementa o contador na tabela `pontos` do banco de dados.
* `POST /api/reset`: Lê a contagem atual, salva-a na tabela `historico` e zera a contagem na tabela `pontos`.
* `DELETE /api/historico/<id>`: Apaga uma sessão específica do histórico.
* `PUT /api/historico/<id>`: Atualiza a "anotação" de uma sessão no histórico.

### `index.html` (A Interface)
* Página web com JavaScript que faz o "polling" da rota `/api/status` a cada 2 segundos.
* Atualiza os contadores ao vivo e a tabela de histórico dinamicamente.
* Contém os botões ("Arquivar", "Salvar Anotação", "Excluir") que chamam as rotas da API.

## 5. Esquema do Banco de Dados (SQLite)

O `monitoramento.db` contém duas tabelas:

1.  **`pontos`**: Armazena a contagem *ao vivo*.
    * `nome_ponto` (TEXTO): "Ponto A" / "Ponto B"
    * `contagem_atual` (INTEIRO)

2.  **`historico`**: Armazena as sessões passadas.
    * `id` (INTEIRO, Chave Primária)
    * `data_reset` (DATETIME)
    * `contagem_ponto_a` (INTEIRO)
    * `contagem_ponto_b` (INTEIRO)
    * `contagem_total` (INTEIRO)
    * `anotacao` (TEXTO)

## 6. Como Executar (Setup)

1.  **Conectar o Hardware:** Monte o circuito conforme a tabela de pinos acima.

2.  **Preparar a Raspberry Pi:**
    * Instale as bibliotecas necessárias:
        ```bash
        pip install Flask RPi.GPIO requests
        ```
    * **(Importante)** Configure o fuso horário da Pi para o horário local (ex: Brasília):
        ```bash
        sudo timedatectl set-timezone America/Sao_Paulo
        ```

3.  **Transferir os Arquivos:** Copie todos os arquivos do projeto (`app.py`, `sensor.py`, `init_db.py` e a pasta `templates`) para um diretório na Raspberry Pi.

4.  **Inicializar o Banco de Dados:**
    * No diretório do projeto, rode este comando **apenas uma vez**:
        ```bash
        python3 init_db.py
        ```
    * *Se você fizer mudanças na estrutura do banco, apague o `monitoramento.db` (`rm monitoramento.db`) e rode o `init_db.py` novamente.*

5.  **Rodar o Projeto (Usando 2 Terminais):**

    * **Terminal 1 (Servidor Web):**
        ```bash
        cd /caminho/do/projeto
        flask run --host=0.0.0.0
        ```

    * **Terminal 2 (Sensores):**
        ```bash
        cd /caminho/do/projeto
        sudo python3 sensor.py
        ```
        *(O `sudo` é necessário para o `RPi.GPIO` acessar os pinos)*

6.  **Acessar o Dashboard:**
    * Em qualquer dispositivo (PC ou celular) na mesma rede Wi-Fi que a Pi, abra um navegador e acesse:
        `http://<10.1.25.46>:5000`