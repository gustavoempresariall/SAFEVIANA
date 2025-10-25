const express = require('express');
const { OAuth2Client } = require('google-auth-library');
const app = express();
const port = 3000;

const CLIENT_ID = 'SUA_CLIENT_ID.apps.googleusercontent.com'; // Substitua pelo seu Client ID
const client = new OAuth2Client(CLIENT_ID);

app.use(express.json());

// Endpoint para lidar com o login do Google
app.post('/auth/google', async (req, res) => {
    const { id_token } = req.body;

    try {
        // Verificar o token com o Google
        const ticket = await client.verifyIdToken({
            idToken: id_token,
            audience: CLIENT_ID,
        });

        const payload = ticket.getPayload();
        const userId = payload['sub']; // ID único do usuário
        const email = payload['email'];
        const name = payload['name'];

        // Aqui você pode:
        // 1. Verificar se o usuário existe no seu banco de dados
        // 2. Criar um novo usuário se necessário
        // 3. Criar uma sessão ou gerar um token JWT

        // Exemplo: Retornar sucesso
        res.json({ success: true, user: { id: userId, email, name } });
    } catch (error) {
        console.error('Erro ao verificar token:', error);
        res.status(401).json({ success: false, error: 'Token inválido' });
    }
});

app.listen(port, () => {
    console.log(`Servidor rodando em http://127.0.0.1:5000${port}`);
});