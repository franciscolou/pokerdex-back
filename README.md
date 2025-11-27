# 🃏 Pokerdex

## 👥 Autores
- Francisco Lou — 2211275  
- Vinicius Araujo — 2210392  

---

**Pokerdex** é uma plataforma para grupos de amigos e entusiastas de pôquer que desejam registrar e acompanhar suas noites de jogatina.  
Com ela, é possível concluir quem mais ganha e quem mais perde e manter um histórico claro das partidas.

---

## 🔑 Entidades principais

O fluxo da aplicação gira em torno de 5 entidades:

1. **Usuário**  
2. **Solicitação**  
3. **Grupo**  
4. **Partida**  
5. **Participação**

---

## 👤 Usuário

O **Usuário** é a base de todo o sistema.  

- Para se cadastrar, o usuário informa:
  - Nome de usuário  
  - E-mail  
  - Senha  

- Para fazer login, é necessário:
  - Nome de usuário  
  - Senha  

Cada usuário pode:
- Criar grupos;  
- Participar de grupos;  
- Criar partidas (dentro de grupos);  
- Ser adicionado a participações de partidas.  

---

## 🎲 Partidas

A **Partida** é o registro de uma noite de pôquer.  
O criador da noite deve informar:

- Nome da partida;  
- Data em que ocorreu;  
- Local do jogo;  
- Cacife mínimo (*buy-in*).  

⚠️ Toda partida deve ser postada em pelo menos **um grupo** (mas pode ser postada em vários).

---

## 👥 Participações

A **Participação** registra o desempenho de um **Usuário** em uma partida.  

Informações obrigatórias de cada participação:
- Jogador;  
- Saldo final;  
- Rebuy (entrada adicional de dinheiro, inclusive quando o jogador já começa a partida acima do *buy-in*).

📌 Regras:
- Cada partida pode ter **infinitas participações**.  
- O jogador adicionado precisa fazer parte de **todos os grupos** nos quais a partida foi postada.

---

## 🌐 Grupos

- São **públicos** e criados por qualquer usuário.  
- Recebem novos membros por meio de **Solicitações** de entrada.  
- As solicitações ficam visíveis na página do grupo, abaixo das informações principais.  

---

## 🏷️ Papéis de usuário em um grupo

Dentro de um grupo, um **Usuário** pode ter até 3 papéis (com permissões cumulativas):

### 👤 Membro
- Pode criar partidas;  
- Pode adicionar participações.  

### 🛡️ Administrador
- Pode aceitar ou recusar solicitações de entrada no grupo;
- Remover membros.

### 👑 Criador
- Possui controle total sobre o grupo:
  - Editar informações do grupo;
  - Editar e apagar partidas postadas no grupo;
  - Conceder ou revogar permissões de administrador;
  - Excluir o grupo.  

⚠️ Importante: se uma partida for postada em um grupo do qual você **não é administrador**, o **criador desse grupo** terá permissão para modificá-la.

---

## 📬 Solicitações

- Um usuário envia uma **solicitação de entrada** para participar de um grupo.  
- Essas solicitações aparecem no menu do grupo.  
- Administradores decidem aceitar ou rejeitar.  

### Transferência de propriedade
- Se o **criador do grupo** sair:
  1. O posto vai para o **administrador mais antigo**;  
  2. Se não houver administradores, vai para o **membro mais antigo**;  
  3. Se o criador for o único membro, o grupo é excluído.

---

## 🚧 Obstáculos pendentes

- Tentamos implementar o envio de **redefinição de senha por e-mail**, mas não conseguimos concluir a integração com provedores de e-mail, apesar de sabermos que não era obrigatória.
Tudo indicava que estava chegando, mas o email não chegava.

---

# 🧪 Como rodar o projeto localmente

## Backend (Django + Docker)

No terminal, dentro da pasta do backend, execute:

```bash
# criar ambiente virtual
python -m venv .venv

# subir containers
docker compose build
docker compose up
```

Após isso, o backend já estará rodando e acessível via **http://localhost:8000**.

---

## Frontend (HTML + CSS + TS)

Dentro da pasta do frontend, execute:

```bash
npm i
npm run dev
```

O frontend ficará disponível normalmente em **http://localhost:5173**.

---    
