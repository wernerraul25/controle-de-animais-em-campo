import sqlite3
from flask import Flask, jsonify, render_template, request
from datetime import datetime

app = Flask(__name__)
DATABASE = 'monitoramento.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# Rota 1: Servir o Front
@app.route('/')
def index():
    return render_template('index.html')

# Rota 2: API para ler os dados
@app.route('/api/status', methods=['GET'])
def get_status():
    conn = get_db_connection()
    
    #  Pega os dados AO VIVO
    pontos_cursor = conn.execute('SELECT nome_ponto, contagem_atual FROM pontos').fetchall()
    status_vivo = {p['nome_ponto']: p['contagem_atual'] for p in pontos_cursor}
    status_vivo['Total'] = sum(status_vivo.values())
    
    #  Pega os dados ARQUIVADOS
    historico_cursor = conn.execute(
        'SELECT id, data_reset, contagem_ponto_a, contagem_ponto_b, contagem_total, anotacao FROM historico ORDER BY data_reset DESC'
    ).fetchall()
    historico = [dict(sessao) for sessao in historico_cursor]
    
    conn.close()
    
    return jsonify({ "live": status_vivo, "history": historico })

# Rota 3: API para a Pi enviar um EVENTO (Sem mudança)
@app.route('/api/evento', methods=['POST'])
def registrar_evento():
    data = request.json
    sensor_disparado = data.get('sensor') # "A" ou "B"
    if not sensor_disparado or sensor_disparado not in ['A', 'B']:
        return jsonify({"erro": "Evento inválido"}), 400
    conn = get_db_connection()
    cursor = conn.cursor()
    nome_ponto = "Ponto A" if sensor_disparado == 'A' else "Ponto B"
    cursor.execute(
        'UPDATE pontos SET contagem_atual = contagem_atual + 1, ultima_atualizacao = ? WHERE nome_ponto = ?',
        (datetime.now(), nome_ponto)
    )
    conn.commit()
    conn.close()
    print(f"API: Evento de passagem no {nome_ponto} registrado.")
    return jsonify({"sucesso": True})

# Rota 4: API para RESETA
#  retorna o ID da sessão que acabou de criar
@app.route('/api/reset', methods=['POST'])
def reset_contadores():
    conn = get_db_connection()
    cursor = conn.cursor()
    ultimo_id_inserido = None # Para saber qual sessão acabamos de criar

    # Passo 1: Ler os valores atuais
    cursor.execute("SELECT nome_ponto, contagem_atual FROM pontos")
    pontos_atuais_raw = cursor.fetchall()
    pontos_atuais = {p['nome_ponto']: p['contagem_atual'] for p in pontos_atuais_raw}
    contagem_a = pontos_atuais.get('Ponto A', 0)
    contagem_b = pontos_atuais.get('Ponto B', 0)
    contagem_total = contagem_a + contagem_b

    if contagem_total > 0:
        # Passo 2: Inserir no historico
        cursor.execute(
            'INSERT INTO historico (data_reset, contagem_ponto_a, contagem_ponto_b, contagem_total) VALUES (?, ?, ?, ?)',
            (datetime.now(), contagem_a, contagem_b, contagem_total)
        )
        ultimo_id_inserido = cursor.lastrowid # Pega o ID da linha que acabamos de inserir
        print(f"API: Histórico salvo (ID: {ultimo_id_inserido}).")
    else:
        print("API: Reset solicitado, mas contagem estava 0.")

    # Passo 3: Zerar os contadores
    cursor.execute('UPDATE pontos SET contagem_atual = 0, ultima_atualizacao = ?', (datetime.now(),))
    
    conn.commit()
    conn.close()
    
    print("API: Contadores ao vivo resetados.")
    # Retorna o ID para o frontend saber qual sessão pode ser nomeada
    return jsonify({"sucesso": True, "ultimo_id": ultimo_id_inserido})

# Rota 5: Limpar os dados salvos
@app.route('/api/historico/<int:id_sessao>', methods=['DELETE'])
def excluir_sessao(id_sessao):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM historico WHERE id = ?', (id_sessao,))
    
    conn.commit()
    conn.close()
    
    print(f"API: Sessão do histórico ID {id_sessao} excluída.")
    return jsonify({"sucesso": True})

# Rota 6: Atualizar anotação
@app.route('/api/historico/<int:id_sessao>', methods=['PUT'])
def atualizar_anotacao(id_sessao):
    data = request.json
    nova_anotacao = data.get('anotacao')
    
    if nova_anotacao is None:
        return jsonify({"erro": "Nenhuma anotação fornecida"}), 400
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('UPDATE historico SET anotacao = ? WHERE id = ?', (nova_anotacao, id_sessao))
    
    conn.commit()
    conn.close()
    
    print(f"API: Anotação da sessão {id_sessao} atualizada.")
    return jsonify({"sucesso": True})


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)