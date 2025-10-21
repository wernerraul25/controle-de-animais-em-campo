import sqlite3

conn = sqlite3.connect('monitoramento.db')
cursor = conn.cursor()

# Tabela 'pontos'
cursor.execute('''
CREATE TABLE IF NOT EXISTS pontos (
    id INTEGER PRIMARY KEY,
    nome_ponto TEXT NOT NULL UNIQUE,
    contagem_atual INTEGER NOT NULL DEFAULT 0,
    ultima_atualizacao DATETIME DEFAULT CURRENT_TIMESTAMP
);
''')

# Tabela 'historico'
cursor.execute('''
CREATE TABLE IF NOT EXISTS historico (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    data_reset DATETIME NOT NULL,
    contagem_ponto_a INTEGER NOT NULL,
    contagem_ponto_b INTEGER NOT NULL,
    contagem_total INTEGER NOT NULL,
    anotacao TEXT DEFAULT '' 
);
''')

# Garante que os pontos existem na tabela 'pontos'
try:
    cursor.execute("INSERT INTO pontos (nome_ponto, contagem_atual) VALUES (?, ?)", ('Ponto A', 0))
    print("Ponto 'A' criado/encontrado.")
except sqlite3.IntegrityError:
    print("Ponto 'A' já existe.")

try:
    cursor.execute("INSERT INTO pontos (nome_ponto, contagem_atual) VALUES (?, ?)", ('Ponto B', 0))
    print("Ponto 'B' criado/encontrado.")
except sqlite3.IntegrityError:
    print("Ponto 'B' já existe.")

# Tenta adicionar a coluna 'anotacao' se a tabela 'historico' já existir
try:
    cursor.execute("ALTER TABLE historico ADD COLUMN anotacao TEXT DEFAULT ''")
    print("Coluna 'anotacao' adicionada ao histórico.")
except sqlite3.OperationalError:
    print("Coluna 'anotacao' já existe.") # Ignora o erro se a coluna já existir

conn.commit()
conn.close()