from flask import Flask, request, jsonify, render_template_string
from threading import Thread
import time
import hashlib
import json
import os
from ecdsa import SigningKey, SECP256k1

# ==================== CLASSES DU TP ====================

class Block:
    def __init__(self, index, transactions, previous_hash, timestamp=None, nonce=0):
        self.index = index
        self.transactions = transactions
        self.previous_hash = previous_hash
        self.timestamp = timestamp or time.time()
        self.nonce = nonce
        self.merkle_root = self.compute_merkle_root(transactions)
        self.hash = self.compute_hash()
    
    def compute_hash(self):
        block_data = {
            'index': self.index,
            'transactions': self.transactions,
            'previous_hash': self.previous_hash,
            'timestamp': self.timestamp,
            'nonce': self.nonce,
            'merkle_root': self.merkle_root
        }
        return hashlib.sha256(json.dumps(block_data, sort_keys=True).encode()).hexdigest()
    
    def compute_merkle_root(self, transactions):
        if not transactions:
            return None
        hashes = [hashlib.sha256(json.dumps(tx, sort_keys=True).encode()).hexdigest() 
                  for tx in transactions]
        while len(hashes) > 1:
            temp = []
            for i in range(0, len(hashes), 2):
                if i+1 < len(hashes):
                    combined = hashes[i] + hashes[i+1]
                else:
                    combined = hashes[i] + hashes[i]
                temp.append(hashlib.sha256(combined.encode()).hexdigest())
            hashes = temp
        return hashes[0]


class Blockchain:
    def __init__(self, difficulty=2):
        self.chain = []
        self.mempool = []
        self.difficulty = difficulty
        self.create_genesis_block()
    
    def create_genesis_block(self):
        # Créer des transactions initiales pour distribuer des coins
        initial_transactions = [
            create_transaction("network", "Alice", 1000),
            create_transaction("network", "Bob", 1000),
            create_transaction("network", "Charlie", 1000),
            create_transaction("network", "miner1", 500)
        ]
        genesis_block = Block(0, initial_transactions, "0")
        self.chain.append(genesis_block)
    
    def add_transaction(self, transaction):
        self.mempool.append(transaction)
        return True
    
    def proof_of_work(self, block):
        block.nonce = 0
        computed_hash = block.compute_hash()
        while not computed_hash.startswith('0' * self.difficulty):
            block.nonce += 1
            computed_hash = block.compute_hash()
        return computed_hash
    
    def mine_block(self, miner_address="miner1"):
        if not self.mempool:
            return None
        
        # Récompense de minage
        reward_tx = create_transaction("network", miner_address, 10)
        self.mempool.append(reward_tx)
        
        new_block = Block(len(self.chain), self.mempool, self.chain[-1].hash)
        new_block.hash = self.proof_of_work(new_block)
        
        self.chain.append(new_block)
        self.mempool = []
        
        print(f"✅ Bloc #{new_block.index} miné: {new_block.hash}")
        return new_block
    
    def is_chain_valid(self):
        for i in range(1, len(self.chain)):
            curr = self.chain[i]
            prev = self.chain[i-1]
            
            if curr.hash != curr.compute_hash():
                print(f"Bloc {i} invalide : hash incorrect")
                return False
            
            if curr.previous_hash != prev.hash:
                print(f"Bloc {i} invalide : previous_hash incorrect")
                return False
            
            if not curr.hash.startswith('0' * self.difficulty):
                print(f"Bloc {i} invalide : proof of work incorrecte")
                return False
        
        return True
    
    def get_balance(self, address):
        balance = 0
        for block in self.chain:
            for tx in block.transactions:
                if tx.get('sender') == address:
                    balance -= tx.get('amount', 0)
                if tx.get('recipient') == address:
                    balance += tx.get('amount', 0)
        
        # Ajouter les transactions en attente
        for tx in self.mempool:
            if tx.get('sender') == address:
                balance -= tx.get('amount', 0)
        
        return balance


def create_transaction(sender, recipient, amount):
    return {
        'sender': sender,
        'recipient': recipient,
        'amount': amount,
        'timestamp': time.time()
    }


def generate_keys():
    priv = SigningKey.generate(curve=SECP256k1)
    pub = priv.get_verifying_key()
    return priv, pub


def sign_transaction(transaction, priv_key):
    tx_str = json.dumps(transaction, sort_keys=True)
    return priv_key.sign(tx_str.encode()).hex()


def verify_transaction(transaction, signature, pub_key):
    tx_str = json.dumps(transaction, sort_keys=True)
    try:
        return pub_key.verify(bytes.fromhex(signature), tx_str.encode())
    except:
        return False


# ==================== INTERFACE WEB HTML ====================

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🔗 Simulateur Blockchain - Nœud {{ node_id }}</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container { max-width: 1400px; margin: 0 auto; }
        
        header {
            text-align: center;
            color: white;
            margin-bottom: 30px;
        }
        
        h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        
        .node-badge {
            background: rgba(255,255,255,0.2);
            padding: 10px 20px;
            border-radius: 20px;
            display: inline-block;
            margin-top: 10px;
        }
        
        .card {
            background: white;
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        
        h2 {
            color: #667eea;
            margin-bottom: 20px;
            font-size: 1.6em;
            border-bottom: 2px solid #f0f0f0;
            padding-bottom: 10px;
        }
        
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 15px;
            margin-bottom: 25px;
        }
        
        .stat-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
        }
        
        .stat-value {
            font-size: 2em;
            font-weight: bold;
            margin-bottom: 5px;
        }
        
        .stat-label { opacity: 0.9; font-size: 0.85em; }
        
        .form-group { margin-bottom: 15px; }
        
        label {
            display: block;
            margin-bottom: 5px;
            color: #555;
            font-weight: 600;
        }
        
        input, select {
            width: 100%;
            padding: 10px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 15px;
            transition: border-color 0.3s;
        }
        
        input:focus, select:focus {
            outline: none;
            border-color: #667eea;
        }
        
        button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 12px 25px;
            border-radius: 8px;
            font-size: 15px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s;
            width: 100%;
        }
        
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }
        
        button:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }
        
        .mine-btn { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }
        .validate-btn { background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); }
        
        .block {
            background: #f8f9fa;
            border-left: 4px solid #667eea;
            padding: 20px;
            margin-bottom: 15px;
            border-radius: 8px;
        }
        
        .block-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 15px;
            flex-wrap: wrap;
            gap: 10px;
        }
        
        .block-index {
            font-size: 1.4em;
            font-weight: bold;
            color: #667eea;
        }
        
        .hash-box {
            font-family: 'Courier New', monospace;
            font-size: 0.75em;
            color: #666;
            word-break: break-all;
            background: #fff;
            padding: 8px;
            border-radius: 5px;
            margin: 5px 0;
        }
        
        .transaction {
            background: white;
            padding: 12px;
            border-radius: 5px;
            margin-bottom: 8px;
            border-left: 3px solid #28a745;
        }
        
        .tx-info {
            display: flex;
            justify-content: space-between;
            font-size: 0.9em;
        }
        
        .message {
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 15px;
            display: none;
            font-size: 0.95em;
        }
        
        .message.success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        
        .message.error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        
        .loading {
            display: inline-block;
            width: 16px;
            height: 16px;
            border: 3px solid rgba(255,255,255,.3);
            border-radius: 50%;
            border-top-color: white;
            animation: spin 1s ease-in-out infinite;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        
        .balance-info {
            background: #e3f2fd;
            padding: 10px;
            border-radius: 5px;
            margin-top: 10px;
            font-size: 0.9em;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🔗 Simulateur Blockchain</h1>
            <div class="node-badge">Nœud {{ node_id }} - Port {{ port }}</div>
        </header>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-value" id="totalBlocks">-</div>
                <div class="stat-label">Blocs Totaux</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="pendingTx">-</div>
                <div class="stat-label">TX en Attente</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="chainValid">-</div>
                <div class="stat-label">État Chaîne</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="difficulty">-</div>
                <div class="stat-label">Difficulté PoW</div>
            </div>
        </div>
        
        <div class="card">
            <h2>💸 Nouvelle Transaction</h2>
            <div id="txMessage" class="message"></div>
            <form id="txForm">
                <div class="form-group">
                    <label for="sender">Expéditeur</label>
                    <input type="text" id="sender" required placeholder="Alice">
                </div>
                <div class="form-group">
                    <label for="recipient">Destinataire</label>
                    <input type="text" id="recipient" required placeholder="Bob">
                </div>
                <div class="form-group">
                    <label for="amount">Montant</label>
                    <input type="number" id="amount" required min="0.01" step="0.01" placeholder="10">
                </div>
                <div class="balance-info" id="senderBalance"></div>
                <button type="submit">Ajouter Transaction</button>
            </form>
        </div>
        
        <div class="card">
            <h2>⛏️ Minage de Bloc</h2>
            <div id="mineMessage" class="message"></div>
            <div class="form-group">
                <label for="minerAddress">Adresse du Mineur</label>
                <input type="text" id="minerAddress" value="miner1" placeholder="miner1">
            </div>
            <button class="mine-btn" onclick="mineBlock()">Miner les Transactions</button>
        </div>
        
        <div class="card">
            <h2>✅ Validation de la Chaîne</h2>
            <div id="validateMessage" class="message"></div>
            <button class="validate-btn" onclick="validateChain()">Valider la Blockchain</button>
        </div>
        
        <div class="card">
            <h2>📊 Blockchain ({{ node_id }})</h2>
            <div id="blockchain"></div>
        </div>
    </div>
    
    <script>
        window.addEventListener('load', () => {
            loadBlockchain();
            loadStats();
        });
        
        // Vérifier le solde lors de la saisie
        document.getElementById('sender').addEventListener('input', async (e) => {
            const sender = e.target.value;
            if (sender.length > 2) {
                try {
                    const response = await fetch(`/balance/${sender}`);
                    const data = await response.json();
                    document.getElementById('senderBalance').innerHTML = 
                        `💰 Solde actuel: <strong>${data.balance}</strong> coins`;
                } catch (error) {
                    document.getElementById('senderBalance').innerHTML = '';
                }
            }
        });
        
        document.getElementById('txForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const sender = document.getElementById('sender').value;
            const recipient = document.getElementById('recipient').value;
            const amount = parseFloat(document.getElementById('amount').value);
            
            const btn = e.target.querySelector('button');
            btn.innerHTML = '<span class="loading"></span> Envoi...';
            btn.disabled = true;
            
            try {
                const response = await fetch('/transactions/new', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ sender, recipient, amount })
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    showMessage('txMessage', data.message, 'success');
                    e.target.reset();
                    document.getElementById('senderBalance').innerHTML = '';
                    loadStats();
                } else {
                    showMessage('txMessage', data.error || data.message, 'error');
                }
                
            } catch (error) {
                showMessage('txMessage', 'Erreur: ' + error.message, 'error');
            }
            
            btn.innerHTML = 'Ajouter Transaction';
            btn.disabled = false;
        });
        
        async function mineBlock() {
            const btn = event.target;
            const minerAddress = document.getElementById('minerAddress').value;
            btn.innerHTML = '<span class="loading"></span> Minage en cours...';
            btn.disabled = true;
            
            try {
                const response = await fetch(`/mine?miner=${minerAddress}`);
                const data = await response.json();
                
                if (response.ok) {
                    showMessage('mineMessage', data.message, 'success');
                    loadBlockchain();
                    loadStats();
                } else {
                    showMessage('mineMessage', data.message || data.error, 'error');
                }
                
            } catch (error) {
                showMessage('mineMessage', 'Erreur: ' + error.message, 'error');
            }
            
            btn.innerHTML = 'Miner les Transactions';
            btn.disabled = false;
        }
        
        async function validateChain() {
            const btn = event.target;
            btn.innerHTML = '<span class="loading"></span> Validation...';
            btn.disabled = true;
            
            try {
                const response = await fetch('/validate');
                const data = await response.json();
                
                showMessage('validateMessage', data.message, data.valid ? 'success' : 'error');
                loadStats();
                
            } catch (error) {
                showMessage('validateMessage', 'Erreur: ' + error.message, 'error');
            }
            
            btn.innerHTML = 'Valider la Blockchain';
            btn.disabled = false;
        }
        
        async function loadBlockchain() {
            try {
                const response = await fetch('/chain');
                const data = await response.json();
                
                const container = document.getElementById('blockchain');
                container.innerHTML = '';
                
                const blocks = [...data.chain].reverse();
                blocks.forEach(block => {
                    const blockDiv = document.createElement('div');
                    blockDiv.className = 'block';
                    
                    const date = new Date(block.timestamp * 1000).toLocaleString('fr-FR');
                    
                    let txHTML = '';
                    block.transactions.forEach(tx => {
                        txHTML += `
                            <div class="transaction">
                                <div class="tx-info">
                                    <span><strong>${tx.sender}</strong> → <strong>${tx.recipient}</strong></span>
                                    <span style="color: #28a745; font-weight: bold;">${tx.amount} coins</span>
                                </div>
                            </div>
                        `;
                    });
                    
                    blockDiv.innerHTML = `
                        <div class="block-header">
                            <span class="block-index">Bloc #${block.index}</span>
                            <span style="color: #999; font-size: 0.85em;">${date}</span>
                        </div>
                        <div style="margin-bottom: 10px;">
                            <strong>Hash:</strong>
                            <div class="hash-box">${block.hash}</div>
                        </div>
                        <div style="margin-bottom: 10px;">
                            <strong>Hash Précédent:</strong>
                            <div class="hash-box">${block.previous_hash}</div>
                        </div>
                        ${block.merkle_root ? `
                        <div style="margin-bottom: 10px;">
                            <strong>Racine Merkle:</strong>
                            <div class="hash-box">${block.merkle_root}</div>
                        </div>` : ''}
                        <div style="margin-bottom: 15px;">
                            <strong>Nonce:</strong> ${block.nonce}
                        </div>
                        <strong>Transactions (${block.transactions.length}):</strong>
                        ${txHTML || '<p style="color: #999; margin-top: 10px;">Aucune transaction (Genesis Block)</p>'}
                    `;
                    
                    container.appendChild(blockDiv);
                });
                
            } catch (error) {
                console.error('Erreur chargement blockchain:', error);
            }
        }
        
        async function loadStats() {
            try {
                const chainResponse = await fetch('/chain');
                const chainData = await chainResponse.json();
                
                const validResponse = await fetch('/validate');
                const validData = await validResponse.json();
                
                document.getElementById('totalBlocks').textContent = chainData.length;
                document.getElementById('pendingTx').textContent = chainData.pending_transactions.length;
                document.getElementById('chainValid').textContent = validData.valid ? '✅ Valide' : '❌ Invalide';
                document.getElementById('difficulty').textContent = chainData.difficulty;
                
            } catch (error) {
                console.error('Erreur chargement stats:', error);
            }
        }
        
        function showMessage(id, message, type) {
            const msgDiv = document.getElementById(id);
            msgDiv.textContent = message;
            msgDiv.className = `message ${type}`;
            msgDiv.style.display = 'block';
            
            setTimeout(() => {
                msgDiv.style.display = 'none';
            }, 5000);
        }
        
        setInterval(() => {
            loadBlockchain();
            loadStats();
        }, 10000);
    </script>
</body>
</html>
'''

# ==================== FLASK APP ====================

def create_app(port=5000, node_id="Node1"):
    app = Flask(__name__)
    app.config['node_id'] = node_id
    app.config['port'] = port
    blockchain = Blockchain(difficulty=3)
    
    @app.route('/')
    def home():
        return render_template_string(HTML_TEMPLATE, node_id=node_id, port=port)
    
    @app.route('/transactions/new', methods=['POST'])
    def new_transaction():
        values = request.get_json()
        required = ['sender', 'recipient', 'amount']
        
        if not all(k in values for k in required):
            return jsonify({'error': 'Champs manquants dans la transaction'}), 400
        
        try:
            amount = float(values['amount'])
            if amount <= 0:
                return jsonify({'error': 'Le montant doit être positif'}), 400
        except ValueError:
            return jsonify({'error': 'Le montant doit être un nombre'}), 400
        
        # Vérifier le solde (sauf pour "network")
        if values['sender'] != 'network':
            balance = blockchain.get_balance(values['sender'])
            if balance < amount:
                return jsonify({
                    'error': f'Solde insuffisant. Solde actuel: {balance} coins'
                }), 400
        
        tx = create_transaction(values['sender'], values['recipient'], amount)
        blockchain.add_transaction(tx)
        
        return jsonify({
            'message': f'Transaction ajoutée au mempool !',
            'transaction': tx,
            'pending_transactions': len(blockchain.mempool)
        }), 201
    
    @app.route('/mine', methods=['GET'])
    def mine():
        miner_address = request.args.get('miner', 'miner1')
        
        if not blockchain.mempool:
            return jsonify({'message': 'Aucune transaction à miner !'}), 400
        
        start_time = time.time()
        block = blockchain.mine_block(miner_address)
        mining_time = time.time() - start_time
        
        return jsonify({
            'message': f'Bloc #{block.index} miné avec succès en {mining_time:.2f}s !',
            'block': {
                'index': block.index,
                'timestamp': block.timestamp,
                'transactions': block.transactions,
                'hash': block.hash,
                'previous_hash': block.previous_hash,
                'merkle_root': block.merkle_root,
                'nonce': block.nonce
            },
            'mining_time': mining_time
        }), 200
    
    @app.route('/chain', methods=['GET'])
    def full_chain():
        chain_data = [{
            'index': block.index,
            'timestamp': block.timestamp,
            'transactions': block.transactions,
            'hash': block.hash,
            'previous_hash': block.previous_hash,
            'merkle_root': block.merkle_root,
            'nonce': block.nonce
        } for block in blockchain.chain]
        
        return jsonify({
            'length': len(chain_data),
            'chain': chain_data,
            'pending_transactions': blockchain.mempool,
            'difficulty': blockchain.difficulty
        }), 200
    
    @app.route('/validate', methods=['GET'])
    def validate_chain():
        is_valid = blockchain.is_chain_valid()
        return jsonify({
            'valid': is_valid,
            'message': 'La blockchain est valide !' if is_valid else 'La blockchain est corrompue !'
        }), 200
    
    @app.route('/balance/<address>', methods=['GET'])
    def get_balance(address):
        balance = blockchain.get_balance(address)
        return jsonify({
            'address': address,
            'balance': balance
        }), 200
    
    return app


# ==================== LANCEMENT DU SERVEUR ====================

if __name__ == "__main__":
    import sys
    
    # Récupérer le port depuis les arguments ou utiliser 5000 par défaut
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    node_id = f"Node{port}"
    
    print(f"\n{'='*60}")
    print(f"🚀 DÉMARRAGE DU NŒUD BLOCKCHAIN")
    print(f"{'='*60}")
    print(f"📍 Nœud ID: {node_id}")
    print(f"🌐 Port: {port}")
    print(f"🔗 URL: http://localhost:{port}")
    print(f"{'='*60}\n")
    
    print(f"💡 Pour lancer un autre nœud, exécutez:")
    print(f"   python {sys.argv[0]} {port+1}\n")
    
    app = create_app(port=port, node_id=node_id)
    app.run(host='0.0.0.0', port=port, debug=False)