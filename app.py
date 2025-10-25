from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory, jsonify, current_app
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime, date, time, timedelta
from flask import current_app
import uuid
from werkzeug.utils import secure_filename
from dateutil.relativedelta import relativedelta
import re
from flask import request, render_template, redirect, url_for, flash
from werkzeug.security import generate_password_hash
from mysql.connector import Error
import os, secrets, hashlib, smtplib, ssl
from datetime import datetime, timedelta
from email.message import EmailMessage
from flask import render_template, request, url_for
from werkzeug.security import generate_password_hash
from flask import Flask, request, jsonify
from google.oauth2 import id_token
from google.auth.transport import requests
from flask_cors import CORS
import secrets
from flask import request, make_response, render_template_string
import os
import asyncio
from flask import Flask, request, Response 
from datetime import datetime, date, time as dtime, timedelta
from flask import current_app
import os, json, uuid, re
from werkzeug.utils import secure_filename

app = Flask(__name__, static_folder="static", template_folder="templates")
UPLOAD_ROOT_ABS = os.path.join(app.root_path, "static", "uploads")

# Configuração do banco de dados
db_config = {
    "host": "localhost",
    "user": "root",  # Altere para o seu usuário do MySQL
    "password": "root",  # Altere para a senha do MySQL
    "database": "safeviana_db"
}

# Função para conectar ao banco de dados
def get_db_connection():
    return mysql.connector.connect(**db_config)


# 🔹 Rota para a página inicial
@app.route("/clientes_corretor.html")
def clientes():
    return render_template("clientes_corretor.html")
@app.route("/")
@app.route("/index")
@app.route("/index.html")
def home():
    return render_template("index.html")

@app.route("/fazercotacao.html")
def fazercotacao():
    return render_template("fazercotacao.html")

@app.route("/sejansparceiro.html")
def sejanossoparceiro():
    return render_template("sejansparceiro.html")
@app.route("/solicitacotacao.html")
def solicitaçãoct():
    return render_template("solicitacotacao.html")

# ROTA PARA LOGIN COM O GOOGLE

app.secret_key = "123456gulv2004"

# Substitua pelo seu Client ID do Google
CLIENT_ID = "478141025582-het74gka9apbbpfaj6mtsijd433kp6fp.apps.googleusercontent.com"

from werkzeug.security import generate_password_hash

@app.route("/auth/google", methods=["POST"])
def google_login():
    try:
        id_token_value = request.json.get("id_token")
        if not id_token_value:
            return jsonify({"success": False, "error": "Nenhum token fornecido"}), 400

        # Valida token no Google
        id_info = id_token.verify_oauth2_token(
            id_token_value, requests.Request(), CLIENT_ID
        )

        google_id = id_info["sub"]
        email = id_info.get("email")
        name = id_info.get("name", "Usuário")

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Verifica se já existe no banco
        cursor.execute("SELECT id, nome, email, tipo FROM usuarios WHERE email = %s", (email,))
        usuario = cursor.fetchone()

        if not usuario:
            senha_fake = generate_password_hash(google_id)  # senha fake baseada no id do Google
            cursor.execute("""
                INSERT INTO usuarios (nome, email, senha_hash, tipo, telefone, genero, cpf, cnpj)
                VALUES (%s, %s, %s, 'Corretor', NULL, NULL, NULL, NULL)
            """, (name, email, senha_fake))
            conn.commit()

            # Busca de volta o usuário inserido
            cursor.execute("SELECT id, nome, email, tipo FROM usuarios WHERE email = %s", (email,))
            usuario = cursor.fetchone()

        # Salva na sessão
        session["user_id"] = usuario["id"]
        session["user_type"] = usuario["tipo"]
        session["name"] = usuario["nome"]
        session["email"] = usuario["email"]

        cursor.close()
        conn.close()

        return jsonify({
            "success": True,
            "redirect": url_for("area_corretor")
        })

    except ValueError:
        return jsonify({"success": False, "error": "Token inválido ou expirado"}), 401
    except Exception as e:
        import traceback
        print("ERRO /auth/google:", traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500


# Login com o google do cliente

@app.route("/auth/google-cliente", methods=["POST"])
def google_login_cliente():
    try:
        id_token_value = request.json.get("id_token")
        if not id_token_value:
            return jsonify({"success": False, "error": "Nenhum token recebido"}), 400

        # Valida token do Google
        id_info = id_token.verify_oauth2_token(
            id_token_value, requests.Request(), CLIENT_ID
        )

        google_id = id_info["sub"]
        email = id_info.get("email")
        nome = id_info.get("name", "Usuário")

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # 🔹 verifica se já existe como cliente (Segurado)
        cursor.execute("SELECT id, nome, email, tipo FROM usuarios WHERE email = %s AND tipo = 'Segurado'", (email,))
        usuario = cursor.fetchone()

        if not usuario:
            senha_fake = generate_password_hash(google_id)
            cursor.execute("""
                INSERT INTO usuarios (nome, email, senha_hash, tipo)
                VALUES (%s, %s, %s, 'Segurado')
            """, (nome, email, senha_fake))
            conn.commit()

            cursor.execute("SELECT id, nome, email, tipo FROM usuarios WHERE email = %s AND tipo = 'Segurado'", (email,))
            usuario = cursor.fetchone()

        # 🔹 cria sessão do cliente
        session["user_id"] = usuario["id"]
        session["user_type"] = usuario["tipo"]  # Segurado
        session["name"] = usuario["nome"]
        session["email"] = usuario["email"]

        cursor.close()
        conn.close()

        return jsonify({"success": True, "redirect": url_for("area_cliente")})

    except ValueError:
        return jsonify({"success": False, "error": "Token inválido ou expirado"}), 401
    except Exception as e:
        import traceback
        print("ERRO /auth/google-cliente:", traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500
    
# Esqueceu senhaa
# ========= Config de E-mail (use variáveis de ambiente em produção) =========

def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

def send_reset_email(to_email: str, reset_url: str):
    msg = EmailMessage()
    msg["Subject"] = "Redefinição de senha - SafeViana"
    msg["From"] = f"{FROM_NAME} <{FROM_EMAIL}>"
    msg["To"] = to_email
    # Texto simples
    msg.set_content(
        f"Olá!\n\nRecebemos uma solicitação para redefinir sua senha.\n"
        f"Clique no link abaixo (ou cole no navegador):\n{reset_url}\n\n"
        "Se você não solicitou, ignore este e-mail.\n"
        "Este link expira em 1 hora.\n\nSafeViana"
    )
    # HTML
    msg.add_alternative(f"""
    <html>
      <body style="font-family:Arial,sans-serif">
        <h2>Redefinição de senha</h2>
        <p>Recebemos uma solicitação para redefinir sua senha.</p>
        <p><a href="{reset_url}" 
              style="display:inline-block;padding:10px 16px;border-radius:8px;
                     background:#10b981;color:#fff;text-decoration:none">
              Redefinir senha
           </a></p>
        <p>Ou copie e cole no navegador:<br>{reset_url}</p>
        <p style="color:#666">Este link expira em 1 hora.</p>
        <p>SafeViana</p>
      </body>
    </html>
    """, subtype="html")

    context = ssl.create_default_context()
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls(context=context)
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)

# ========== Página/rota: solicitar redefinição ==========
@app.route("/recuperar_senha.html", methods=["GET", "POST"])
def recuperar_senha():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        if not email:
            return render_template("recuperar_senha.html", error="Informe seu e-mail.")

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Procurar usuário
        cursor.execute("SELECT id, email FROM usuarios WHERE email = %s LIMIT 1", (email,))
        user = cursor.fetchone()

        # Sempre responder sucesso (para evitar enumeração de e-mails)
        # Mas, se o usuário existir, gerar e enviar token
        if user:
            token = secrets.token_urlsafe(32)
            token_hash = _hash_token(token)
            expires_at = datetime.utcnow() + timedelta(hours=1)

            cursor.execute(
                "INSERT INTO password_resets (user_id, token_hash, expires_at) VALUES (%s, %s, %s)",
                (user["id"], token_hash, expires_at)
            )
            conn.commit()

            reset_url = url_for("redefinir_senha", token=token, _external=True)
            try:
                send_reset_email(user["email"], reset_url)
            except Exception as e:
                app.logger.exception("Falha ao enviar e-mail de redefinição: %s", e)

        cursor.close()
        conn.close()
        return render_template("recuperar_senha_enviado.html")

    # GET
    return render_template("recuperar_senha.html")


# ========== Página/rota: definir nova senha ==========
@app.route("/redefinir_senha/<token>", methods=["GET", "POST"])
def redefinir_senha(token):
    token_hash = _hash_token(token)

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT pr.id, pr.user_id, pr.expires_at, pr.used, u.email
        FROM password_resets pr
        JOIN usuarios u ON u.id = pr.user_id
        WHERE pr.token_hash = %s
        LIMIT 1
    """, (token_hash,))
    pr = cursor.fetchone()

    # Token inexistente/expirado/uso prévio
    if (not pr) or pr["used"] == 1 or pr["expires_at"] < datetime.utcnow():
        cursor.close()
        conn.close()
        return render_template("token_invalido.html")

    if request.method == "POST":
        senha = request.form.get("senha") or ""
        confirmar = request.form.get("confirmar_senha") or ""

        if len(senha) < 6:
            cursor.close()
            conn.close()
            return render_template("redefinir_senha.html", token=token,
                                   error="A senha deve ter pelo menos 6 caracteres.")

        if senha != confirmar:
            cursor.close()
            conn.close()
            return render_template("redefinir_senha.html", token=token,
                                   error="As senhas não coincidem.")

        nova_hash = generate_password_hash(senha)

        # Atualiza senha e marca token como usado
        cursor.execute("UPDATE usuarios SET senha_hash = %s WHERE id = %s", (nova_hash, pr["user_id"]))
        cursor.execute("UPDATE password_resets SET used = 1 WHERE id = %s", (pr["id"],))
        conn.commit()

        cursor.close()
        conn.close()
        return render_template("redefinir_senha_ok.html")

    cursor.close()
    conn.close()
    return render_template("redefinir_senha.html", token=token)

from flask import send_from_directory

@app.route('/imagens/<path:filename>')
def imagens(filename):
    return send_from_directory('imagens', filename)


# CONFIG PARA GMAIL:

# --------- Gmail SMTP ---------
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465  # SSL direto
SMTP_USER = "negociosempresariall01@gmail.com"        # <= seu Gmail
SMTP_PASS = "rjlu xvsy oeaq espt"  # <= Senha de App (16 chars, sem espaços)
FROM_NAME = "SafeViana"
FROM_EMAIL = SMTP_USER             # Gmail exige remetente igual à conta

def send_reset_email(to_email: str, reset_url: str):
    msg = EmailMessage()
    msg["Subject"] = "Redefinição de senha - SafeViana"
    msg["From"] = f"{FROM_NAME} <{FROM_EMAIL}>"
    msg["To"] = to_email
    msg.set_content(
        f"Olá!\n\nRecebemos uma solicitação para redefinir sua senha.\n"
        f"Clique no link abaixo (ou cole no navegador):\n{reset_url}\n\n"
        "Se você não solicitou, ignore este e-mail.\n"
        "O link expira em 1 hora.\n\nSafeViana"
    )
    msg.add_alternative(f"""
    <html><body style="font-family:Arial,sans-serif">
      <h2>Redefinição de senha</h2>
      <p>Clique abaixo para redefinir sua senha:</p>
      <p><a href="{reset_url}" style="display:inline-block;padding:10px 16px;border-radius:8px;background:#10b981;color:#fff;text-decoration:none">
         Redefinir senha
      </a></p>
      <p>Ou copie e cole no navegador:<br>{reset_url}</p>
      <p style="color:#666">Este link expira em 1 hora.</p>
      <p>SafeViana</p>
    </body></html>
    """, subtype="html")

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context) as server:
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)



@app.route("/relatorio_corretor.html")
def relatorio():
     if "user_id" not in session or session.get("user_type") != "Corretor":
        return redirect(url_for("corretor_login"))
    
     conn = get_db_connection()
     cursor = conn.cursor(dictionary=True)
     cursor.execute("SELECT nome FROM usuarios WHERE id = %s", (session["user_id"],))
     usuario = cursor.fetchone()
     cursor.close()
     conn.close()
    
     nome_corretor = usuario["nome"] if usuario else "Corretor"
    # ⬆️ FIM DO BLOCO

     return render_template("relatorio_corretor.html", corretor_nome=nome_corretor)

# 🔹 Área do Corretor
def render_template_with_vars(filename, **context):
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Substituir todas as variáveis no template
        for key, value in context.items():
            content = content.replace('{{ ' + key + ' }}', str(value))
        
        return content
    except FileNotFoundError:
        return f"Arquivo {filename} não encontrado", 404

@app.route("/area_corretor")
def area_corretor():
    if "user_id" in session and session.get("user_type") == "Corretor":
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, nome, email, telefone, biografia, foto_de_perfil
            FROM usuarios
            WHERE id = %s
        """, (session["user_id"],))
        usuario = cursor.fetchone()
        cursor.close()
        conn.close()

        # DEBUG para checar se veio algo do banco
        current_app.logger.debug("area_corretor - usuario fetched: %s", usuario)

        if usuario:
            nome_corretor = usuario.get("nome", "Corretor")
            email_corretor = usuario.get("email", "email@exemplo.com")
            telefone_corretor = usuario.get("telefone", "")
            biografia_corretor = usuario.get("biografia", "")
            foto_corretor = usuario.get("foto_de_perfil", "")
        else:
            # fallback seguro caso não encontre no banco
            nome_corretor = "Corretor"
            email_corretor = "email@exemplo.com"
            telefone_corretor = ""
            biografia_corretor = ""
            foto_corretor = ""

        # Atualiza a sessão com os dados atuais
        session["corretor_nome"] = nome_corretor
        session["corretor_email"] = email_corretor
        session["corretor_foto"] = foto_corretor

        return render_template(
            "area_corretor.html",
            corretor_nome=nome_corretor,
            corretor_email=email_corretor,
            corretor_telefone=telefone_corretor,
            corretor_biografia=biografia_corretor,
            corretor_foto=foto_corretor
        )
    else:
        flash("Acesso restrito! Faça login como corretor.", "danger")
        return redirect(url_for("corretor_login"))


UPLOAD_FOLDER = 'static/uploads/perfis'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER  # Certifique-se de que está configurado no app

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/api/corretor/atualizar-perfil", methods=["POST"])
def atualizar_perfil_corretor():
    if "user_id" not in session or session.get("user_type") != "Corretor":
        return jsonify({"status": "error", "message": "Acesso não autorizado"}), 403

    # Obter dados do formulário
    nome = request.form.get("nome")
    email = request.form.get("email")
    telefone = request.form.get("telefone")
    biografia = request.form.get("biografia")

    if not nome or not email:
        return jsonify({"status": "error", "message": "Nome e email são obrigatórios"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        foto_path = None
        
        # Processar upload da foto se existir
        if 'foto' in request.files:
            file = request.files['foto']
            
            if file and file.filename != '' and allowed_file(file.filename):
                # Verificar tamanho do arquivo
                file.seek(0, os.SEEK_END)
                file_length = file.tell()
                file.seek(0)
                
                if file_length > MAX_FILE_SIZE:
                    return jsonify({"status": "error", "message": "Arquivo muito grande. Máximo 5MB."}), 400
                
                # Criar diretório se não existir
                if not os.path.exists(UPLOAD_FOLDER):
                    os.makedirs(UPLOAD_FOLDER)
                
                # Gerar nome único para o arquivo
                filename = secure_filename(file.filename)
                unique_filename = f"{uuid.uuid4().hex}_{filename}"
                file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
                
                # Salvar arquivo
                file.save(file_path)
                # Salvar caminho relativo no banco (sem 'static/')
                foto_path = f"uploads/perfis/{unique_filename}"
                
                # Remover foto antiga se existir
                cursor.execute("SELECT foto_de_perfil FROM usuarios WHERE id = %s", (session["user_id"],))
                old_photo_result = cursor.fetchone()
                
                if old_photo_result and old_photo_result[0]:
                    old_photo_path = os.path.join(app.config['UPLOAD_FOLDER'], old_photo_result[0].split('/')[-1])
                    if os.path.exists(old_photo_path) and old_photo_path != file_path:
                        os.remove(old_photo_path)

        # Atualizar banco de dados
        if foto_path:
            cursor.execute(
                """
                UPDATE usuarios 
                SET nome = %s, email = %s, telefone = %s, biografia = %s, foto_de_perfil = %s
                WHERE id = %s
                """,
                (nome, email, telefone, biografia, foto_path, session["user_id"])
            )
        else:
            cursor.execute(
                """
                UPDATE usuarios 
                SET nome = %s, email = %s, telefone = %s, biografia = %s
                WHERE id = %s
                """,
                (nome, email, telefone, biografia, session["user_id"])
            )
        
        conn.commit()

        # Atualizar TODOS os dados na sessão
        session["corretor_nome"] = nome
        session["corretor_email"] = email
        if foto_path:
            session["corretor_foto"] = foto_path
        else:
            # Manter a foto atual ou limpar se não houver
            cursor.execute("SELECT foto_de_perfil FROM usuarios WHERE id = %s", (session["user_id"],))
            current_photo = cursor.fetchone()
            session["corretor_foto"] = current_photo[0] if current_photo and current_photo[0] else ""

        # Retornar caminho da foto com url_for para uso imediato no frontend
        foto_url = url_for('static', filename=session["corretor_foto"]) if session["corretor_foto"] else ""

        return jsonify({
            "status": "success",
            "message": "Perfil atualizado com sucesso!",
            "foto": foto_url  # Retorna /static/uploads/perfis/nome.jpg
        })

    except Exception as e:
        conn.rollback()
        current_app.logger.error(f"Erro ao atualizar perfil: {str(e)}")
        return jsonify({"status": "error", "message": "Erro ao atualizar perfil. Tente novamente."}), 500

    finally:
        cursor.close()
        conn.close()

    
    # 🔹 Rota para a página inicial do corretor
@app.route("/areacr.html")
def area_corretor_login():
    if "user_id" not in session or session.get("user_type") != "Corretor":
        return redirect(url_for("corretor_login"))

    # Buscar o nome do corretor logado
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT nome FROM usuarios WHERE id = %s", (session["user_id"],))
    usuario = cursor.fetchone()
    cursor.close()
    conn.close()
    
    nome_corretor = usuario["nome"] if usuario else "Corretor"
    
    return render_template_with_vars('areacr.html', corretor_nome=nome_corretor)

def render_template_with_vars(filename, **context):
    """
    Renderiza um arquivo HTML substituindo variáveis no formato {{ var_name }}
    """
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Substituir todas as variáveis no template
        for key, value in context.items():
            placeholder = '{{ ' + key + ' }}'
            content = content.replace(placeholder, str(value))
        
        return content
    except FileNotFoundError:
        return f"Arquivo {filename} não encontrado", 404
    except Exception as e:
        return f"Erro ao renderizar template: {str(e)}", 500
    
    
    # 🔹 Rota para adicionar cliente do corretor via formulário
@app.route("/adicionar_cliente", methods=["POST"])
def adicionar_cliente():
    if "user_id" not in session or session.get("user_type") != "Corretor":
        flash("Acesso não autorizado!", "danger")
        return redirect(url_for("corretor_login"))

    # Obter o ID do corretor da sessão
    corretor_id = session.get("user_id")
    
    if not corretor_id:
        flash("Erro de autenticação. Faça login novamente.", "danger")
        return redirect(url_for("corretor_login"))

    # Coletar dados do formulário
    tipo_pessoa = request.form.get("tipoPessoa")
    nome = request.form.get("nome")
    cpfcnpj = request.form.get("cpfcnpj")
    email = request.form.get("email")
    status = request.form.get("status")
    telefone = request.form.get("telefone")
    empresa = request.form.get("empresa")
    rginsc = request.form.get("rginsc")
    cep = request.form.get("cep")
    endereco = request.form.get("endereco")
    numero = request.form.get("numero")
    bairro = request.form.get("bairro")
    cidade = request.form.get("cidade")
    estado = request.form.get("estado")
    tipo_seguro = request.form.get("tipoSeguro")
    placa = request.form.get("placa")
    chassi = request.form.get("chassi")
    renavam = request.form.get("renavam")
    cor = request.form.get("cor")
    ano = request.form.get("ano")
    observacoes = request.form.get("observacoes")

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = """
    INSERT INTO clientes_corretor (
        tipo_pessoa, nome, cpf_cnpj, email, status, telefone, nome_fantasia, rg_inscricao,
        cep, endereco, numero, bairro, cidade, estado, tipo_seguro,
        placa, chassi, renavam, cor, ano_modelo, observacoes, corretor_id
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""
        valores = (
            tipo_pessoa, nome, cpfcnpj, email, status, telefone, empresa, rginsc,
            cep, endereco, numero, bairro, cidade, estado, tipo_seguro,
            placa, chassi, renavam, cor, ano, observacoes, corretor_id
        )
        cursor.execute(sql, valores)
        conn.commit()
        flash("Cliente cadastrado com sucesso!", "success")
    except Exception as e:
        print("Erro ao inserir cliente:", e)
        flash("Erro ao cadastrar cliente. Verifique os dados e tente novamente.", "danger")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for("clientes"))

# 🔹 Rota para clientes recentes (JSON)
@app.route("/clientes-recentes", methods=["GET"])
def clientes_recentes():
    if "user_id" not in session or session.get("user_type") != "Corretor":
        return jsonify({"erro": "Acesso não autorizado"}), 403

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT 
                nome,
                email,
                telefone,
                DATE_FORMAT(CURDATE(), '%d/%m/%Y') AS data_cadastro,
                tipo_seguro AS apolices,
                status FROM clientes_corretor
            ORDER BY id DESC
            LIMIT 5
        """)
        
        clientes = cursor.fetchall()

        cursor.close()
        conn.close()

        return jsonify(clientes)
    
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

# 🔹 Rotas para servir arquivos estáticos fora de /static
@app.route('/css/<path:filename>')
def servir_css(filename):
    return send_from_directory(os.path.join(os.getcwd(), 'css'), filename)

@app.route("/visu_clientes_corretor.html")
def visualizar_clientes():
    if "user_id" not in session or session.get("user_type") != "Corretor":
        return redirect(url_for("corretor_login"))

    def _wa_number(raw: str | None) -> str | None:
        if not raw:
            return None
        import re
        digits = re.sub(r"\D+", "", raw).lstrip("0")
        if not digits:
            return None
        if digits.startswith("55"):
            return digits
        if len(digits) in (10, 11):
            return "55" + digits
        return digits

    def _join_nonempty(items, sep=" • "):
        return sep.join([str(x).strip() for x in items if str(x or "").strip()])

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT id, nome, tipo_pessoa, email, telefone, status,
               endereco, bairro, cidade
          FROM clientes_corretor
         WHERE corretor_id = %s
         ORDER BY nome ASC
    """, (session["user_id"],))
    clientes = cursor.fetchall() or []

    by_id = {}
    for c in clientes:
        c["telefone_wa"] = _wa_number(c.get("telefone"))
        c["apolices"] = []
        by_id[c["id"]] = c

    ids = [c["id"] for c in clientes]
    if ids:
        in_clause = ", ".join(["%s"] * len(ids))
        cursor.execute(f"""
            SELECT
                a.id                           AS apolice_id,
                a.cliente_id,
                a.numero_apolice,
                a.tipo_apolice,
                a.valor_apolice,
                DATE_FORMAT(a.data_inicio , '%d/%m/%Y %H:%i') AS data_inicio_fmt,
                DATE_FORMAT(a.data_termino, '%d/%m/%Y %H:%i') AS data_termino_fmt,
                a.status,
                a.veiculo,
                a.placa,
                a.ano_modelo,

                /* >>> NOVOS CAMPOS PARA O "VENCIMENTO" */
                a.parcelas,
                DATE_FORMAT(a.primeiro_vencimento, '%d/%m/%Y') AS primeiro_vencimento_fmt

            FROM apolices a
           WHERE a.corretor_id = %s
             AND a.cliente_id IN ({in_clause})
           ORDER BY COALESCE(a.data_inicio, a.created_at) DESC
        """, [session["user_id"], *ids])

        for ap in (cursor.fetchall() or []):
            tipo = (ap.get("tipo_apolice") or "").strip().lower()
            if tipo == "auto":
                detalhe = _join_nonempty([ap.get("veiculo"), ap.get("placa"), ap.get("ano_modelo")], sep=" • ")
            else:
                cli = by_id.get(ap["cliente_id"], {})
                detalhe = _join_nonempty([cli.get("endereco"), cli.get("bairro"), cli.get("cidade")], sep=", ")

            ap["detalhe_curto"] = detalhe or "-"
            ap["tipo_com_detalhe"] = _join_nonempty([ap.get("tipo_apolice"), ap["detalhe_curto"]], sep=" — ")

            by_id.get(ap["cliente_id"], {}).get("apolices", []).append(ap)

    cursor.execute("SELECT nome FROM usuarios WHERE id = %s", (session["user_id"],))
    usuario = cursor.fetchone()
    nome_corretor = (usuario or {}).get("nome", "Corretor")

    cursor.close(); conn.close()

    return render_template(
        "visu_clientes_corretor.html",
        clientes=clientes,
        corretor_nome=nome_corretor
    )

@app.route("/excluir_cliente/<int:id>", methods=["POST"])
def excluir_cliente(id):
    if "user_id" not in session or session.get("user_type") != "Corretor":
        flash("Acesso não autorizado!", "danger")
        return redirect(url_for("corretor_login"))

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM clientes_corretor WHERE id = %s", (id,))
        conn.commit()
        flash("Cliente excluído com sucesso!", "success")
    except Exception as e:
        print("Erro ao excluir cliente:", e)
        flash("Erro ao excluir cliente.", "danger")
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for("visualizar_clientes"))

@app.route("/editar_cliente_corretor/<int:id>", methods=["GET", "POST"])
def editar_cliente(id):
    if "user_id" not in session or session.get("user_type") != "Corretor":
        flash("Acesso não autorizado!", "danger")
        return redirect(url_for("corretor_login"))

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    try:
        # Garante que o cliente é do corretor logado
        cur.execute("""
            SELECT *
              FROM clientes_corretor
             WHERE id = %s AND corretor_id = %s
        """, (id, session["user_id"]))
        cliente = cur.fetchone()
        if not cliente:
            flash("Cliente não encontrado.", "warning")
            return redirect(url_for("visualizar_clientes"))

        if request.method == "POST":
            f = request.form

            # Normaliza status para o ENUM da tabela
            status_raw = (f.get("status") or "").strip()
            status_ok = status_raw if status_raw in ("Ativo", "Inativo", "Pendente") else "Ativo"

            # Só colunas que existem em clientes_corretor
            payload = {
                "tipo_pessoa":   (f.get("tipo_pessoa") or None),
                "nome":          (f.get("nome") or None),
                "cpf_cnpj":      (f.get("cpfcnpj") or None),
                "email":         (f.get("email") or None),
                "telefone":      (f.get("telefone") or None),
                "nome_fantasia": (f.get("empresa") or None),
                "rg_inscricao":  (f.get("rginsc") or None),
                "cep":           (f.get("cep") or None),
                "endereco":      (f.get("endereco") or None),
                "numero":        (f.get("numero") or None),
                "bairro":        (f.get("bairro") or None),
                "cidade":        (f.get("cidade") or None),
                "estado":        (f.get("estado") or None),
                "status":        status_ok,
                "tipo_seguro":   (f.get("tipoSeguro") or None),
                "placa":         (f.get("placa") or None),
                "chassi":        (f.get("chassi") or None),
                "renavam":       (f.get("renavam") or None),
                "cor":           (f.get("cor") or None),
                "ano_modelo":    (f.get("ano") or None),
                "observacoes":   (f.get("observacoes") or None),
                # As colunas abaixo existem na tabela, mas não estão no formulário.
                # Se você quiser editá-las aqui, adicione inputs no HTML:
                # "tipo_apolice":  ...,
                # "valor_apolice": ...,
                # "data_inicio":   ...,
                # "data_termino":  ...,
            }

            set_clause = ", ".join([f"{col} = %s" for col in payload.keys()])
            values = list(payload.values()) + [id, session["user_id"]]

            cur.execute(f"""
                UPDATE clientes_corretor
                   SET {set_clause}
                 WHERE id = %s AND corretor_id = %s
            """, values)
            conn.commit()

            flash("Cliente atualizado com sucesso!", "success")
            return redirect(url_for("visualizar_clientes"))

        # GET
        return render_template("editar_cliente_corretor.html", cliente=cliente)

    except Exception as e:
        conn.rollback()
        print("Erro ao salvar cliente:", e)
        flash(f"Erro ao salvar cliente: {e}", "danger")
        return redirect(url_for("visualizar_clientes"))
    finally:
        try:
            cur.close(); conn.close()
        except:
            pass

# helpers (mantive aqui pra ficar completo)
def _parse_dt(s):
    """Aceita 'YYYY-MM-DDTHH:MM', 'YYYY-MM-DD HH:MM' ou 'YYYY-MM-DD'."""
    if not s:
        return None
    s = s.strip().replace("T", " ")
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None

def _parse_date(s):
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None

def _parse_int(s):
    try:
        return int(s)
    except (TypeError, ValueError):
        return None
    
# Opções permitidas (devem bater com o ENUM da tabela `apolices`)
ALLOWED_FORMAS_PAGAMENTO = (
    "Boleto",
    "Cartão de crédito",
    "PIX",
    "Débito em conta",
    "Outro",
)

@app.route("/adicionar_apolices_corretor.html", methods=["GET"])
def pagina_adicionar_apolice():
    if "user_id" not in session or session.get("user_type") != "Corretor":
        flash("Acesso não autorizado!", "danger")
        return redirect(url_for("corretor_login"))

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Nome do corretor (topbar)
        cursor.execute("SELECT nome FROM usuarios WHERE id = %s", (session["user_id"],))
        usuario = cursor.fetchone()
        nome_corretor = (usuario or {}).get("nome", "Corretor")

        # ✅ Somente clientes do corretor logado
        cursor.execute("""
            SELECT id, nome
              FROM clientes_corretor
             WHERE status = 'Ativo'
               AND corretor_id = %s
             ORDER BY nome ASC
        """, (session["user_id"],))
        clientes = cursor.fetchall()
        
        # ✅ Lista fixa (ou vinda de tabela, se quiser)
        seguradoras = [
            {"nome": "Porto Seguro"},
            {"nome": "Bradesco Seguros"},
            {"nome": "SulAmérica"},
            {"nome": "Tokio Marine"},
            {"nome": "Allianz"},
            {"nome": "HDI Seguros"},
            {"nome": "Mapfre"},
            {"nome": "Liberty"},
        ]


    except Exception as e:
        print("Erro ao carregar clientes para nova apólice:", e)
        flash("Erro ao carregar clientes.", "danger")
        clientes = []
        nome_corretor = "Corretor"
    finally:
        try:
            cursor.close(); conn.close()
        except:
            pass

    return render_template(
        "adicionar_apolices_corretor.html",
        clientes=clientes,
        seguradoras=seguradoras,
        corretor_nome=nome_corretor,
        formas_pagamento=ALLOWED_FORMAS_PAGAMENTO   # mantém se você usa o select de forma de pagamento
    )


from datetime import datetime, date

ALLOWED_FORMAS_PAGAMENTO = {"Boleto", "CartaoCredito", "Pix", "DebitoConta", "Transferencia", "Dinheiro"}

def _parse_dt(s):
    """Aceita 'YYYY-MM-DDTHH:MM', 'YYYY-MM-DD HH:MM' ou apenas 'YYYY-MM-DD'."""
    if not s:
        return None
    s = s.strip().replace("T", " ")
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None

def _parse_date(s):
    if not s:
        return None
    try:
        return datetime.strptime(s.strip(), "%Y-%m-%d").date()
    except ValueError:
        return None

def _parse_int(s):
    try:
        return int(s)
    except (TypeError, ValueError):
        return None

def _canonicalize_fp(v: str | None) -> str | None:
    if not v:
        return None
    raw = (v or "").strip()
    direct = {
        "Boleto": "Boleto",
        "Pix": "Pix",
        "Dinheiro": "Dinheiro",
        "CartaoCredito": "CartaoCredito",
        "Cartão de Crédito": "CartaoCredito",
        "Cartao de Credito": "CartaoCredito",
        "Cartão Credito": "CartaoCredito",
        "Crédito": "CartaoCredito",
        "Credito": "CartaoCredito",
        "Cartao": "CartaoCredito",
        "DebitoConta": "DebitoConta",
        "Débito em Conta": "DebitoConta",
        "Debito em Conta": "DebitoConta",
        "Débito": "DebitoConta",
        "Debito": "DebitoConta",
        "Transferencia": "Transferencia",
        "Transferência": "Transferencia",
    }
    if raw in direct:
        return direct[raw]
    import unicodedata, re
    key = unicodedata.normalize("NFKD", raw)
    key = "".join(c for c in key if not unicodedata.combining(c))
    key = re.sub(r"[\s_-]+", "", key).lower()
    aliases = {
        "boleto": "Boleto",
        "pix": "Pix",
        "dinheiro": "Dinheiro",
        "cartaocredito": "CartaoCredito",
        "cartaodecredito": "CartaoCredito",
        "credito": "CartaoCredito",
        "cartao": "CartaoCredito",
        "debitoemconta": "DebitoConta",
        "debito": "DebitoConta",
        "transferencia": "Transferencia",
        "transferenciabancaria": "Transferencia",
    }
    code = aliases.get(key)
    return code if code in ALLOWED_FORMAS_PAGAMENTO else None


@app.route("/salvar_apolice", methods=["POST"])
def salvar_apolice():
    if "user_id" not in session or session.get("user_type") != "Corretor":
        flash("Acesso não autorizado!", "danger")
        return redirect(url_for("corretor_login"))

    # Dados do form
    cliente_id        = request.form.get("cliente_id")
    numero_apol       = request.form.get("numero_apolice")         # opcional
    numero_proposta   = request.form.get("numero_proposta")        # opcional
    tipo_seguro       = request.form.get("tipo_seguro")            # opcional
    tipo_apolice      = request.form.get("tipo_apolice")
    seguradora        = request.form.get("seguradora")
    valor             = request.form.get("valor") or 0
    data_inicio_raw   = request.form.get("data_inicio")            # datetime-local
    data_fim_raw      = request.form.get("data_fim")               # datetime-local
    status_form       = request.form.get("status")

    # Cobrança
    primeiro_venc_raw = request.form.get("primeiro_vencimento")    # date (YYYY-MM-DD)
    parcelas          = _parse_int(request.form.get("parcelas"))

    # Forma de pagamento (canoniza para o ENUM)
    forma_pagamento_raw = request.form.get("forma_pagamento")
    forma_pagamento = _canonicalize_fp(forma_pagamento_raw) or "Boleto"

    # Campos opcionais (auto)
    veiculo     = request.form.get("veiculo")
    placa       = request.form.get("placa")
    chassi      = request.form.get("chassi")
    renavam     = request.form.get("renavam")
    cor         = request.form.get("cor_veiculo")
    ano_modelo  = request.form.get("ano_modelo")
    observacoes = request.form.get("observacoes")

    # Normaliza datas/horas
    data_inicio         = _parse_dt(data_inicio_raw)
    data_fim            = _parse_dt(data_fim_raw)
    primeiro_vencimento = _parse_date(primeiro_venc_raw)  # coluna DATE

    # Mapeia status do form -> ENUM do banco
    def map_status(s):
        mapa = {
            "Ativo": "Ativa",
            "Inativo": "Cancelada",
            "Pendente": "Pendente",
            "Ativa": "Ativa",
            "Cancelada": "Cancelada",
            "Vencida": "Vencida",
        }
        return mapa.get((s or "").strip(), "Ativa")

    status_db = map_status(status_form)

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO apolices
                (cliente_id, corretor_id, numero_apolice, numero_proposta, tipo_seguro, tipo_apolice, seguradora,
                 valor_apolice, data_inicio, data_termino,
                 primeiro_vencimento, parcelas, forma_pagamento, status,
                 veiculo, placa, chassi, renavam, cor, ano_modelo, observacoes)
            VALUES
                (%s, %s, %s, %s, %s, %s,
                 %s, %s, %s,
                 %s, %s, %s, %s,
                 %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            cliente_id, session["user_id"], numero_apol, numero_proposta, tipo_seguro, tipo_apolice, seguradora,
            valor, data_inicio, data_fim,
            primeiro_vencimento, parcelas, forma_pagamento, status_db,
            veiculo, placa, chassi, renavam, cor, ano_modelo, observacoes
        ))

        conn.commit()
        flash("Apólice criada com sucesso!", "success")

    except Exception as e:
        print("Erro ao salvar apólice:", e)
        flash("Erro ao salvar apólice.", "danger")
    finally:
        try:
            cursor.close(); conn.close()
        except:
            pass

    return redirect(url_for("apolices"))

@app.route("/apolices_corretor.html")
def apolices():
    if "user_id" not in session or session.get("user_type") != "Corretor":
        flash("Acesso não autorizado!", "danger")
        return redirect(url_for("corretor_login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Nome do corretor (topbar)
    cursor.execute("SELECT nome FROM usuarios WHERE id = %s", (session["user_id"],))
    usuario = cursor.fetchone()

    # Lista de apólices do corretor logado + campos extras para a linha expansível
    cursor.execute("""
        SELECT
            a.id                AS apolice_id,        -- id da apólice
            a.cliente_id        AS id,                -- id do cliente (compat com template)
            c.nome              AS nome,
            c.cpf_cnpj          AS cpf,
            a.seguradora        AS seguradora,       
                   
            a.numero_apolice    AS numero_apolice,
            a.numero_proposta   AS numero_proposta,
            a.tipo_apolice,
            a.valor_apolice,

            -- Datas já formatadas para a tabela (dd/mm/aaaa hh:mm)
            DATE_FORMAT(a.data_inicio , '%d/%m/%Y %H:%i') AS data_inicio_fmt,
            DATE_FORMAT(a.data_termino, '%d/%m/%Y %H:%i') AS data_termino_fmt,

            -- Campos usados no bloco expansível
            a.veiculo,
            a.cor,
            a.placa,
            a.ano_modelo,
            a.parcelas,
            a.primeiro_vencimento,   -- DATE (render já lida com [:10])
            a.forma_pagamento,
            a.observacoes,

            -- Endereço/cidade do cliente (para residencial/empresarial/vida)
            c.endereco AS endereco,
            c.cidade   AS cidade,

            -- Status normalizado para o front
            CASE a.status
                WHEN 'Ativa'     THEN 'Ativo'
                WHEN 'Pendente'  THEN 'Pendente'
                WHEN 'Cancelada' THEN 'Inativo'
                WHEN 'Vencida'   THEN 'Inativo'
                ELSE a.status
            END AS status

        FROM apolices a
        JOIN clientes_corretor c ON c.id = a.cliente_id
        WHERE a.corretor_id = %s
        ORDER BY COALESCE(a.data_inicio, a.created_at) DESC
    """, (session["user_id"],))

    apolices = cursor.fetchall()
    cursor.close()
    conn.close()

    nome_corretor = usuario["nome"] if usuario else "Corretor"
    return render_template("apolices_corretor.html", apolices=apolices, corretor_nome=nome_corretor)

@app.route("/get_anexo/<int:apolice_id>")
def get_anexo(apolice_id):
    """
    Retorna o caminho do arquivo anexo de uma apólice (tabela apolices_segurado)
    para exibir dinamicamente na página apolices_corretor.html.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)

        cur.execute("""
            SELECT arquivo_anexo
            FROM apolices_segurado
            WHERE apolice_id = %s
            LIMIT 1
        """, (apolice_id,))

        row = cur.fetchone()
        cur.close()
        conn.close()

        if not row or not row["arquivo_anexo"]:
            return jsonify({"success": True, "arquivo": None})

        nome_arquivo = os.path.basename(row["arquivo_anexo"])
        return jsonify({
            "success": True,
            "arquivo": {
                "nome": nome_arquivo,
                "caminho": row["arquivo_anexo"]
            }
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500



@app.route("/detalhes_cliente/<int:id>", methods=["GET", "POST"])
def detalhes_cliente(id):  # id = apólice.id
    if "user_id" not in session or session.get("user_type") != "Corretor":
        flash("Acesso não autorizado!", "danger")
        return redirect(url_for("corretor_login"))
    
    SEGURADORAS_FIXAS = [
    {"nome": "Porto Seguro"},
    {"nome": "Bradesco Seguros"},
    {"nome": "Itaú Seguros"},
    {"nome": "SulAmérica"},
    {"nome": "Allianz"},
    {"nome": "Tokio Marine"},
    {"nome": "HDI Seguros"},
    {"nome": "Mapfre"},
]

    def to_db_status(s):
        mapa = {
            "Ativo": "Ativa", "Ativa": "Ativa",
            "Inativo": "Cancelada", "Cancelada": "Cancelada",
            "Pendente": "Pendente",
            "Vencida": "Vencida",
        }
        return mapa.get((s or "").strip(), "Ativa")

    try:
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)

        if request.method == "POST":
            f = request.form

            print("📨 Dados recebidos no POST:", request.form)


            # Normalização de datas/horas e números
            data_inicio         = _parse_dt(f.get("data_inicio"))            # datetime-local
            data_termino        = _parse_dt(f.get("data_termino"))           # datetime-local
            primeiro_vencimento = _parse_date(f.get("primeiro_vencimento"))  # DATE
            parcelas            = _parse_int(f.get("parcelas"))

            forma_pagamento = f.get("forma_pagamento") or None
            if forma_pagamento and forma_pagamento not in ALLOWED_FORMAS_PAGAMENTO:
                # Se vier algo fora do permitido, mantém o valor atual do banco
                forma_pagamento = None

            try:
                cur.execute("""
                    UPDATE apolices
                       SET numero_apolice       = %s,
                           numero_proposta      = %s,
                           tipo_apolice         = %s,
                           seguradora           = %s,
                           valor_apolice        = %s,
                           data_inicio          = %s,
                           data_termino         = %s,
                           primeiro_vencimento  = %s,
                           parcelas             = %s,
                           forma_pagamento      = COALESCE(%s, forma_pagamento),
                           veiculo              = %s,
                           placa                = %s,
                           chassi               = %s,
                           renavam              = %s,
                           cor                  = %s,
                           ano_modelo           = %s,
                           observacoes          = %s,
                           status               = %s,
                           updated_at           = NOW()
                     WHERE id = %s AND corretor_id = %s
                """, (
                    (f.get("numero_apolice") or None),
                    (f.get("numero_proposta") or None),
                    f.get("tipo_apolice"),
                    f.get("seguradora"),
                    (f.get("valor_apolice") or None),
                    data_inicio,
                    data_termino,
                    primeiro_vencimento,
                    parcelas,
                    forma_pagamento,
                    f.get("veiculo"),
                    f.get("placa"),
                    f.get("chassi"),
                    f.get("renavam"),
                    f.get("cor"),
                    f.get("ano_modelo"),
                    f.get("observacoes"),
                    to_db_status(f.get("status")),
                    id, session["user_id"]
                ))

                # 2️⃣ Atualiza a tabela apolices_segurado (sincroniza dados principais)
                cur.execute("""
                    UPDATE apolices_segurado
                       SET seguradora          = %s,
                           tipo_apolice        = %s,
                           valor_apolice       = %s,
                           data_inicio         = %s,
                           data_termino        = %s,
                           status              = %s,
                           updated_at          = NOW()
                     WHERE apolice_id = %s
                """, (
                    f.get("seguradora"),
                    f.get("tipo_apolice"),
                    f.get("valor_apolice") or None,
                    data_inicio,
                    data_termino,
                    to_db_status(f.get("status")),
                    id
                ))

                conn.commit()
                flash("Apólice e dados do segurado atualizados com sucesso!", "success")
                
                conn.commit()
                flash("Apólice atualizada com sucesso!", "success")
            except Exception as e:
                msg = str(e)
                if "1062" in msg and "numero_apolice" in msg:
                    flash("Já existe uma apólice com esse número para este corretor.", "warning")
                elif "1062" in msg and "numero_proposta" in msg:
                    flash("Já existe uma proposta com esse número para este corretor.", "warning")
                else:
                    print("Erro ao atualizar apólice:", e)
                    flash("Erro ao atualizar apólice.", "danger")
            return redirect(url_for("detalhes_cliente", id=id))

        # GET: carrega apólice + cliente
        cur.execute("""
            SELECT a.*,
                   c.id    AS cliente_id,
                   c.nome  AS cliente_nome,
                   c.tipo_pessoa, c.cpf_cnpj, c.email, c.telefone,
                   c.nome_fantasia, c.rg_inscricao, c.cep, c.endereco,
                   c.numero, c.bairro, c.cidade, c.estado
              FROM apolices a
              JOIN clientes_corretor c ON c.id = a.cliente_id
             WHERE a.id = %s AND a.corretor_id = %s
        """, (id, session["user_id"]))
        ap = cur.fetchone()

        if not ap:
            flash("Apólice não encontrada.", "warning")
            return redirect(url_for("apolices"))

        # --- normaliza forma_pagamento para casar com as opções do <select> ---
        fp_raw = (ap.get("forma_pagamento") or "").strip()
        alias_map = {
            "Cartão de Crédito": "CartaoCredito",
            "Cartao de Crédito": "CartaoCredito",
            "CartaoCredito": "CartaoCredito",
            "Crédito": "CartaoCredito",
            "Credito": "CartaoCredito",
            "Cartao": "CartaoCredito",

            "Débito em Conta": "DebitoConta",
            "Debito em Conta": "DebitoConta",
            "Débito": "DebitoConta",
            "Debito": "DebitoConta",
            "DebitoConta": "DebitoConta",

            "Transferência": "Transferencia",
            "Transferencia": "Transferencia",

            "Pix": "Pix",
            "Dinheiro": "Dinheiro",
            "Boleto": "Boleto",
        }
        fp_norm = alias_map.get(fp_raw, fp_raw)
        if fp_norm not in ALLOWED_FORMAS_PAGAMENTO:
            # fallback seguro
            fp_norm = "Boleto" if not fp_norm else fp_norm
        ap["forma_pagamento"] = fp_norm

        # Mapeia para o rótulo usado no front
        ap["status_front"] = {"Ativa": "Ativo", "Cancelada": "Inativo"}.get(ap["status"], ap["status"])

        cliente = {
            "id": ap["cliente_id"], "nome": ap["cliente_nome"],
            "tipo_pessoa": ap.get("tipo_pessoa"), "cpf_cnpj": ap.get("cpf_cnpj"),
            "email": ap.get("email"), "telefone": ap.get("telefone"),
            "nome_fantasia": ap.get("nome_fantasia"), "rg_inscricao": ap.get("rg_inscricao"),
            "cep": ap.get("cep"), "endereco": ap.get("endereco"), "numero": ap.get("numero"),
            "bairro": ap.get("bairro"), "cidade": ap.get("cidade"), "estado": ap.get("estado"),
        }

        # Nome do corretor (topo)
        cur.execute("SELECT nome FROM usuarios WHERE id = %s", (session["user_id"],))
        usuario = cur.fetchone()
        corretor_nome = (usuario or {}).get("nome", "Corretor")

    except Exception as e:
        print("Erro em detalhes_cliente:", e)
        flash("Erro ao carregar/atualizar apólice.", "danger")
        return redirect(url_for("apolices"))
    finally:
        try:
            cur.close(); conn.close()
        except:
            pass

    # Envia também as formas de pagamento para popular o <select> do template
    return render_template(
        "detalhes_apolice.html",
        ap=ap,
        cliente=cliente,
        corretor_nome=corretor_nome,
        formas_pagamento=ALLOWED_FORMAS_PAGAMENTO,
        seguradoras=SEGURADORAS_FIXAS
    )


# ----------------- Helpers p/ parsing -----------------
from decimal import Decimal, InvalidOperation

def _parse_decimal(val):
    """
    Converte string para Decimal, aceitando:
    - '1234,56'  (pt-BR)
    - '1.234,56' (pt-BR com milhar)
    - '1234.56'  (padrão)
    - 'R$ 1.234,56'
    Retorna None se vazio/ inválido.
    """
    if val is None:
        return None
    s = str(val).strip().replace('R$', '').replace(' ', '')
    # Se houver '.' e ',' e o ponto vier antes da vírgula, tratamos '.' como separador de milhar
    if '.' in s and ',' in s and s.find('.') < s.find(','):
        s = s.replace('.', '').replace(',', '.')
    else:
        s = s.replace(',', '.')
    if s == '':
        return None
    try:
        return Decimal(s)
    except (InvalidOperation, ValueError):
        return None

def _parse_prob(val):
    """Converte para int 0..100; None se vazio."""
    if val is None or str(val).strip() == '':
        return None
    try:
        p = int(str(val).strip())
    except ValueError:
        return None
    return max(0, min(100, p))


@app.route("/enviar_apolice/<int:apolice_id>", methods=["POST"])
def enviar_apolice(apolice_id):
    if "user_id" not in session or session.get("user_type") != "Corretor":
        return {"error": "Acesso não autorizado"}, 403

    try:
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)

        # Busca apólice + cliente
        cur.execute("""
            SELECT a.*, c.id AS cliente_id, c.nome AS cliente_nome,
                   c.cpf_cnpj, c.email, c.telefone,
                   c.endereco, c.cidade, c.estado
            FROM apolices a
            JOIN clientes_corretor c ON c.id = a.cliente_id
            WHERE a.id = %s AND a.corretor_id = %s
        """, (apolice_id, session["user_id"]))
        apolice = cur.fetchone()

        if not apolice:
            return {"error": "Apólice não encontrada"}, 404

        # Insere ou atualiza em apolices_segurado
        cur.execute("""
            INSERT INTO apolices_segurado
                (apolice_id, cliente_id, cliente_nome, cpf, email, telefone,
                 numero_apolice, numero_proposta, tipo_apolice, valor_apolice,
                 data_inicio, data_termino, parcelas, primeiro_vencimento,
                 forma_pagamento, observacoes, status, seguradora, endereco,
                 cidade, estado, enviado_em)
            VALUES
                (%s, %s, %s, %s, %s, %s,
                 %s, %s, %s, %s,
                 %s, %s, %s, %s,
                 %s, %s, %s, %s, %s,
                 %s, %s, NOW())
            ON DUPLICATE KEY UPDATE
                cliente_nome = VALUES(cliente_nome),
                cpf = VALUES(cpf),
                email = VALUES(email),
                telefone = VALUES(telefone),
                numero_apolice = VALUES(numero_apolice),
                numero_proposta = VALUES(numero_proposta),
                tipo_apolice = VALUES(tipo_apolice),
                valor_apolice = VALUES(valor_apolice),
                data_inicio = VALUES(data_inicio),
                data_termino = VALUES(data_termino),
                parcelas = VALUES(parcelas),
                primeiro_vencimento = VALUES(primeiro_vencimento),
                forma_pagamento = VALUES(forma_pagamento),
                observacoes = VALUES(observacoes),
                status = VALUES(status),
                seguradora = VALUES(seguradora),
                endereco = VALUES(endereco),
                cidade = VALUES(cidade),
                estado = VALUES(estado),
                enviado_em = NOW()
        """, (
            apolice["id"], apolice["cliente_id"], apolice["cliente_nome"],
            apolice.get("cpf_cnpj"), apolice.get("email"), apolice.get("telefone"),
            apolice.get("numero_apolice"), apolice.get("numero_proposta"),
            apolice.get("tipo_apolice"), apolice.get("valor_apolice"),
            apolice.get("data_inicio"), apolice.get("data_termino"),
            apolice.get("parcelas"), apolice.get("primeiro_vencimento"),
            apolice.get("forma_pagamento"), apolice.get("observacoes"),
            apolice.get("status"), apolice.get("seguradora"),
            apolice.get("endereco"), apolice.get("cidade"), apolice.get("estado")
        ))

        conn.commit()
        return {"success": True, "message": "Apólice enviada com sucesso!"}, 200

    except Exception as e:
        import traceback
        traceback.print_exc()  # 🔥 Mostra erro completo no console
        return {"error": str(e)}, 500

    finally:
        try:
            cur.close()
            conn.close()
        except:
            pass



# ----------------- Rotas -----------------

UPLOAD_BASE = os.path.join('static', 'uploads', 'propostas')

ALLOWED_DOCS = {'.pdf','.doc','.docx','.xls','.xlsx','.csv','.txt','.ppt','.pptx','.zip','.rar','.7z','.odt','.ods'}
ALLOWED_IMGS = {'.jpg','.jpeg','.png','.webp','.gif'}

def _ensure_dir(path: str):
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)

def _ext_ok(filename: str, allowed: set) -> bool:
    ext = os.path.splitext(filename)[1].lower()
    return ext in allowed

def _unique_name(original: str) -> str:
    base, ext = os.path.splitext(secure_filename(original))
    return f"{base}__{uuid.uuid4().hex}{ext}"

@app.route("/adicionar_proposta", methods=["POST"])
def adicionar_proposta():
    if "user_id" not in session or session.get("user_type") != "Corretor":
        flash("Acesso não autorizado!", "danger")
        return redirect(url_for("corretor_login"))

    cliente          = request.form.get('cliente')
    cpf_cliente      = formatar_cpf(request.form.get("cpf_cliente"))
    numero_proposta  = request.form.get("proposta")
    validade         = request.form.get("validade")
    tipo             = request.form.get("tipo")
    seguradora       = request.form.get("seguradora")
    anotacoes        = request.form.get("anotacoes")
    status           = request.form.get("status")
    valor_total_raw  = request.form.get("valor_total")
    prob_raw         = request.form.get("probabilidade")
    prazo_raw        = request.form.get("prazo_estimado")

    valor_total   = _parse_decimal(valor_total_raw)
    probabilidade = _parse_prob(prob_raw)
    try:
        prazo_estimado = int(prazo_raw) if prazo_raw not in (None, "") else None
    except:
        prazo_estimado = None

    corretor_id = session["user_id"]

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 1) insere a proposta (sem anexos ainda)
        cursor.execute("""
            INSERT INTO propostas
                (cliente, cpf_cliente, numero_proposta, validade, tipo, seguradora, anotacoes, status,
                 corretor_id, valor_total, probabilidade, prazo_estimado,
                 documentos_json, fotos_json)
            VALUES
                (%s, %s, %s, %s, %s, %s, %s, %s,
                 %s, %s, %s, %s,
                 %s, %s)
        """, (cliente, cpf_cliente, numero_proposta, validade, tipo, seguradora, anotacoes, status,
              corretor_id, valor_total, probabilidade, prazo_estimado,
              None, None))
        conn.commit()

        proposta_id = cursor.lastrowid

        # 2) salva arquivos no disco e monta arrays de paths
        base_dir = os.path.join(UPLOAD_BASE, str(proposta_id))
        docs_dir = os.path.join(base_dir, "documentos")
        imgs_dir = os.path.join(base_dir, "fotos")
        _ensure_dir(docs_dir)
        _ensure_dir(imgs_dir)

        documentos_paths = []
        fotos_paths = []

        # Documentos
        for f in request.files.getlist("documentos[]"):
            if not f or not f.filename:
                continue
            if not _ext_ok(f.filename, ALLOWED_DOCS):
                continue
            fname = _unique_name(f.filename)
            full_path = os.path.join(docs_dir, fname)
            f.save(full_path)
            url_rel = os.path.join('static', 'uploads', 'propostas', str(proposta_id), 'documentos', fname).replace('\\','/')
            documentos_paths.append(url_rel)

        # Fotos
        for f in request.files.getlist("fotos[]"):
            if not f or not f.filename:
                continue
            if not _ext_ok(f.filename, ALLOWED_IMGS):
                continue
            fname = _unique_name(f.filename)
            full_path = os.path.join(imgs_dir, fname)
            f.save(full_path)
            url_rel = os.path.join('static', 'uploads', 'propostas', str(proposta_id), 'fotos', fname).replace('\\','/')
            fotos_paths.append(url_rel)

        # 3) grava os arrays como JSON nas colunas
        documentos_json = json.dumps(documentos_paths, ensure_ascii=False) if documentos_paths else None
        fotos_json      = json.dumps(fotos_paths, ensure_ascii=False) if fotos_paths else None

        cursor.execute("""
            UPDATE propostas
               SET documentos_json = %s,
                   fotos_json      = %s
             WHERE id = %s
        """, (documentos_json, fotos_json, proposta_id))

        conn.commit()

        msg = "Proposta cadastrada com sucesso!"
        if (documentos_paths or fotos_paths):
            msg += f" ({len(documentos_paths)} documento(s), {len(fotos_paths)} foto(s) anexados)"
        flash(msg, "success")

    except Exception as e:
        print("Erro ao inserir proposta / salvar uploads:", e)
        try:
            conn.rollback()
        except: pass
        flash("Erro ao cadastrar proposta.", "danger")
    finally:
        try:
            cursor.close(); conn.close()
        except: pass

    return redirect(url_for("propostas"))



@app.route("/propostas_corretor.html")
def propostas():
    if "user_id" not in session or session.get("user_type") != "Corretor":
        return redirect(url_for("corretor_login"))

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Buscar SOMENTE as propostas do corretor logado, incluindo os novos campos
        cursor.execute("""
            SELECT
                id, cliente, cpf_cliente, numero_proposta, validade, tipo, seguradora, anotacoes, status,
                valor_total, probabilidade, prazo_estimado, documentos_json, fotos_json
            FROM propostas
            WHERE corretor_id = %s
            ORDER BY id DESC
        """, (session["user_id"],))
        propostas = cursor.fetchall()

        # Nome do corretor
        cursor.execute("SELECT nome FROM usuarios WHERE id = %s", (session["user_id"],))
        usuario = cursor.fetchone()
        nome_corretor = usuario["nome"] if usuario else "Corretor"

    except Exception as e:
        print("Erro ao buscar propostas:", e)
        propostas = []
        nome_corretor = "Corretor"
    finally:
        try:
            cursor.close()
            conn.close()
        except Exception:
            pass

    return render_template(
        "propostas_corretor.html",
        propostas_corretor=propostas,
        corretor_nome=nome_corretor
    )


@app.route("/atualizar_proposta", methods=["POST"])
def atualizar_proposta():
    if "user_id" not in session or session.get("user_type") != "Corretor":
        flash("Acesso não autorizado!", "danger")
        return redirect(url_for("corretor_login"))

    # -------- helpers locais --------
    def _to_yyyy_mm_dd(s):
        if not s:
            return None
        s = str(s).strip()
        if re.match(r"^\d{4}-\d{2}-\d{2}", s):
            return s[:10]
        m = re.match(r"^(\d{2})/(\d{2})/(\d{4})$", s)
        if m:
            return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
        try:
            from datetime import datetime
            d = datetime.fromisoformat(s.replace("/", "-"))
            return d.strftime("%Y-%m-%d")
        except Exception:
            return None

    def _basename(p):
        return os.path.basename(str(p or ""))

    def _norm_path(p: str) -> str:
        """normaliza para comparar/filtrar: tira barra inicial e barras invertidas"""
        return str(p or "").replace("\\", "/").lstrip("/")

    def _as_file_objects(lst):
        out = []
        for it in lst or []:
            if isinstance(it, str):
                out.append({"path": it, "original": _basename(it)})
            elif isinstance(it, dict):
                obj = {
                    "path": it.get("path") or it.get("filename") or it.get("url") or "",
                    "original": it.get("original") or it.get("name") or _basename(it.get("path") or it.get("filename") or ""),
                    "mimetype": it.get("mimetype"),
                    "size": it.get("size"),
                }
                out.append(obj)
        return out

    def _dedupe_by_path(items):
        seen = set()
        out = []
        for it in items:
            p = _norm_path(it.get("path"))
            if p and p not in seen:
                seen.add(p)
                it["path"] = p  # já salvo normalizado (sem barra inicial)
                out.append(it)
        return out

    # -------- campos do formulário --------
    id_proposta       = request.form.get("id_proposta")
    cliente           = request.form.get("cliente")
    cpf_cliente       = formatar_cpf(request.form.get("cpf_cliente"))
    numero_proposta   = request.form.get("proposta")
    validade          = _to_yyyy_mm_dd(request.form.get("validade"))
    tipo              = request.form.get("tipo")
    seguradora        = request.form.get("seguradora")
    anotacoes         = request.form.get("anotacoes")
    status            = request.form.get("status")
    valor_total_raw   = request.form.get("valor_total")
    prob_raw          = request.form.get("probabilidade")
    prazo_raw         = request.form.get("prazo_estimado")

    # HIDDENs com anexos já existentes e remoções vindos do front
    existing_docs_json   = request.form.get("existing_documentos_json") or "[]"
    existing_fotos_json  = request.form.get("existing_fotos_json") or "[]"
    remove_docs_json     = request.form.get("remove_documentos_json") or "[]"
    remove_fotos_json    = request.form.get("remove_fotos_json") or "[]"

    try: existing_docs_form  = json.loads(existing_docs_json)
    except Exception: existing_docs_form = []
    try: existing_fotos_form = json.loads(existing_fotos_json)
    except Exception: existing_fotos_form = []
    try: remove_docs_form    = json.loads(remove_docs_json)
    except Exception: remove_docs_form = []
    try: remove_fotos_form   = json.loads(remove_fotos_json)
    except Exception: remove_fotos_form = []

    # normaliza listas de remoção para SET de paths (normalizados)
    def _to_remove_set(lst):
        s = set()
        for it in lst or []:
            if isinstance(it, str):
                s.add(_norm_path(it))
            elif isinstance(it, dict):
                s.add(_norm_path(it.get("path") or it.get("filename") or it.get("url")))
        return s

    remove_docs_set  = _to_remove_set(remove_docs_form)
    remove_fotos_set = _to_remove_set(remove_fotos_form)

    valor_total   = _parse_decimal(valor_total_raw)
    probabilidade = _parse_prob(prob_raw)
    try:
        prazo_estimado = int(prazo_raw) if prazo_raw not in (None, "") else None
    except Exception:
        prazo_estimado = None

    add_docs = 0
    add_fotos = 0

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Atualiza a tabela principal
        cursor.execute("""
            UPDATE propostas
               SET cliente         = %s,
                   cpf_cliente     = %s,
                   numero_proposta = %s,
                   validade        = %s,
                   tipo            = %s,
                   seguradora      = %s,
                   anotacoes       = %s,
                   status          = %s,
                   valor_total     = %s,
                   probabilidade   = %s,
                   prazo_estimado  = %s
             WHERE id = %s
        """, (cliente, cpf_cliente, numero_proposta, validade, tipo, seguradora,
              anotacoes, status, valor_total, probabilidade, prazo_estimado, id_proposta))

        # Atualiza espelho (tente)
        try:
            cursor.execute("""
                UPDATE propostas_segurado
                   SET segurado_nome   = %s,
                       cpf_cliente     = %s,
                       numero_proposta = %s,
                       validade        = %s,
                       tipo            = %s,
                       seguradora      = %s,
                       anotacoes       = %s,
                       status          = %s,
                       valor_total     = %s,
                       probabilidade   = %s,
                       prazo_estimado  = %s,
                       atualizado_em   = NOW()
                 WHERE proposta_id = %s
            """, (cliente, cpf_cliente, numero_proposta, validade, tipo, seguradora,
                  anotacoes, status, valor_total, probabilidade, prazo_estimado, id_proposta))
        except Exception:
            pass

        # ---------- anexos ----------
        # Lê o que já está no BD
        cursor.execute("SELECT documentos_json, fotos_json FROM propostas WHERE id=%s", (id_proposta,))
        row = cursor.fetchone()

        antigos_docs_db  = []
        antigos_fotos_db = []
        if row:
            try: antigos_docs_db  = json.loads(row[0]) if row[0] else []
            except Exception: antigos_docs_db = []
            try: antigos_fotos_db = json.loads(row[1]) if row[1] else []
            except Exception: antigos_fotos_db = []

        # Normaliza para objetos + paths normalizados
        antigos_docs_db   = _dedupe_by_path(_as_file_objects(antigos_docs_db))
        antigos_fotos_db  = _dedupe_by_path(_as_file_objects(antigos_fotos_db))
        existentes_docs   = _dedupe_by_path(_as_file_objects(existing_docs_form))
        existentes_fotos  = _dedupe_by_path(_as_file_objects(existing_fotos_form))

        # Base = união (BD + form)
        base_docs  = _dedupe_by_path(antigos_docs_db + existentes_docs)
        base_fotos = _dedupe_by_path(antigos_fotos_db + existentes_fotos)

        # --------- APLICA REMOÇÕES ---------
        if remove_docs_set:
            base_docs = [d for d in base_docs if _norm_path(d.get("path")) not in remove_docs_set]
        if remove_fotos_set:
            base_fotos = [f for f in base_fotos if _norm_path(f.get("path")) not in remove_fotos_set]

        # pastas físicas
        base_dir = os.path.join(UPLOAD_BASE, str(id_proposta))
        docs_dir = os.path.join(base_dir, "documentos")
        imgs_dir = os.path.join(base_dir, "fotos")
        _ensure_dir(docs_dir)
        _ensure_dir(imgs_dir)

        # novos documentos
        novos_docs_objs = []
        for f in request.files.getlist("documentos[]"):
            if not f or not f.filename:
                continue
            if not _ext_ok(f.filename, ALLOWED_DOCS):
                continue
            fname = _unique_name(f.filename)
            full_path = os.path.join(docs_dir, fname)
            f.save(full_path)
            url_rel = os.path.join("static", "uploads", "propostas", str(id_proposta), "documentos", fname).replace("\\", "/")
            size = None
            try: size = os.path.getsize(full_path)
            except Exception: pass
            novos_docs_objs.append({
                "original": f.filename,
                "path": _norm_path(url_rel),
                "mimetype": f.mimetype,
                "size": size
            })
            add_docs += 1

        # novas fotos
        novos_fotos_objs = []
        for f in request.files.getlist("fotos[]"):
            if not f or not f.filename:
                continue
            if not _ext_ok(f.filename, ALLOWED_IMGS):
                continue
            fname = _unique_name(f.filename)
            full_path = os.path.join(imgs_dir, fname)
            f.save(full_path)
            url_rel = os.path.join("static", "uploads", "propostas", str(id_proposta), "fotos", fname).replace("\\", "/")
            size = None
            try: size = os.path.getsize(full_path)
            except Exception: pass
            novos_fotos_objs.append({
                "original": f.filename,
                "path": _norm_path(url_rel),
                "mimetype": f.mimetype,
                "size": size
            })
            add_fotos += 1

        # mescla finais (existentes filtrados + novos)
        docs_final  = _dedupe_by_path(base_docs  + novos_docs_objs)
        fotos_final = _dedupe_by_path(base_fotos + novos_fotos_objs)

        # --------- (opcional) remover fisicamente os arquivos apagados ---------
        # Só remova se realmente estavam no BD e foram pedidos na lista
        def _try_delete(relpath_norm):
            try:
                # monta caminho absoluto com base no UPLOAD_BASE (evita sair da pasta)
                abs_path = os.path.join(UPLOAD_ROOT_ABS, relpath_norm) 
                if os.path.isfile(abs_path):
                    os.remove(abs_path)
            except Exception:
                pass

        for it in antigos_docs_db:
            p = _norm_path(it.get("path"))
            if p in remove_docs_set:
                _try_delete(p)

        for it in antigos_fotos_db:
            p = _norm_path(it.get("path"))
            if p in remove_fotos_set:
                _try_delete(p)

        # grava JSONs
        cursor.execute("""
            UPDATE propostas
               SET documentos_json = %s,
                   fotos_json      = %s
             WHERE id = %s
        """, (json.dumps(docs_final, ensure_ascii=False) if docs_final else None,
              json.dumps(fotos_final, ensure_ascii=False) if fotos_final else None,
              id_proposta))

        conn.commit()

        if add_docs or add_fotos or remove_docs_set or remove_fotos_set:
            msg = "✅ Proposta atualizada."
            if add_docs or add_fotos:
                msg += f" Novos anexos: {add_docs} documento(s), {add_fotos} foto(s)."
            if remove_docs_set or remove_fotos_set:
                msg += f" Removidos: {len(remove_docs_set)} doc(s), {len(remove_fotos_set)} foto(s)."
            flash(msg, "success")
        else:
            flash("✅ Proposta atualizada com sucesso!", "propostas-success")

    except Exception as e:
        import traceback
        print("\n" + "="*70)
        print("❌ ERRO AO ATUALIZAR PROPOSTA:")
        print("Tipo:", type(e))
        print("Mensagem:", e)
        traceback.print_exc()
        print("="*70 + "\n")
        try:
            conn.rollback()
        except Exception:
            pass
        flash("Erro ao atualizar proposta.", "propostas-error")
    finally:
        try:
            cursor.close()
            conn.close()
        except Exception:
            pass

    return redirect(url_for("propostas"))

@app.route("/excluir_proposta", methods=["POST"])
def excluir_proposta():
    if "user_id" not in session or session.get("user_type") != "Corretor":
        flash("Acesso não autorizado!", "danger")
        return redirect(url_for("corretor_login"))

    id_proposta = request.form.get("id_proposta")

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 🔹 Primeiro exclui da tabela propostas_segurado (dependente)
        cursor.execute("DELETE FROM propostas_segurado WHERE proposta_id = %s", (id_proposta,))

        # 🔹 Depois exclui da tabela principal
        cursor.execute("DELETE FROM propostas WHERE id = %s", (id_proposta,))

        conn.commit()
        flash("✅ Proposta excluída com sucesso!", "propostas-success")

    except Exception as e:
        import traceback
        print("\n" + "="*70)
        print("❌ ERRO AO EXCLUIR PROPOSTA:")
        print("Tipo:", type(e))
        print("Mensagem:", e)
        traceback.print_exc()
        print("="*70 + "\n")
        flash("Erro ao excluir proposta.", "propostas-error")

    finally:
        cursor.close()
        conn.close()

    return redirect(url_for("propostas"))



# ================== SINISTROS: UPLOADS CONFIG & HELPERS ==================

UPLOAD_BASE_SIN = os.path.join('static', 'uploads', 'sinistros')  # base pública (igual Propostas)

ALLOWED_DOCS = {'.pdf','.doc','.docx','.xls','.xlsx','.csv','.txt','.ppt','.pptx','.zip','.rar','.7z','.odt','.ods'}
ALLOWED_IMGS = {'.jpg','.jpeg','.png','.webp','.gif'}

def _ensure_dir(path: str):
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)

def _ext_ok(filename: str, allowed: set) -> bool:
    ext = os.path.splitext(filename)[1].lower()
    return ext in allowed

def _unique_name(original: str) -> str:
    base, ext = os.path.splitext(secure_filename(original or "file"))
    return f"{base}__{uuid.uuid4().hex}{ext}"

def _basename(p):
    return os.path.basename(str(p or ""))

def _norm_path(p: str) -> str:
    """normaliza para comparar/filtrar: tira barra inicial e barras invertidas"""
    return str(p or "").replace("\\", "/").lstrip("/")

def _as_file_objects(lst):
    out = []
    for it in lst or []:
        if isinstance(it, str):
            out.append({"path": it, "original": _basename(it)})
        elif isinstance(it, dict):
            obj = {
                "path": it.get("path") or it.get("filename") or it.get("url") or "",
                "original": it.get("original") or it.get("name") or _basename(it.get("path") or it.get("filename") or ""),
                "mimetype": it.get("mimetype"),
                "size": it.get("size"),
            }
            out.append(obj)
    return out

def _dedupe_by_path(items):
    seen = set()
    out = []
    for it in items:
        p = _norm_path(it.get("path"))
        if p and p not in seen:
            seen.add(p)
            it["path"] = p
            out.append(it)
    return out

def _to_remove_set(lst):
    s = set()
    for it in lst or []:
        if isinstance(it, str):
            s.add(_norm_path(it))
        elif isinstance(it, dict):
            s.add(_norm_path(it.get("path") or it.get("filename") or it.get("url")))
    return s



@app.route("/sinistros_corretor.html")
def sinistros():
    if "user_id" not in session or session.get("user_type") != "Corretor":
        return redirect(url_for("corretor_login"))

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT *
            FROM sinistros
            WHERE corretor_id = %s
            ORDER BY id DESC
        """, (session["user_id"],))
        sinistros_corretor = cursor.fetchall() or []

        # Normaliza JSONs (opcional)
        for s in sinistros_corretor:
            for key in ("documentos_json","fotos_json","imagens"):
                if key in s and isinstance(s[key], (bytes, bytearray)):
                    try: s[key] = s[key].decode()
                    except: s[key] = str(s[key])
            try: s["documentos_json"] = json.loads(s.get("documentos_json") or "[]")
            except: s["documentos_json"] = []
            try: s["fotos_json"] = json.loads(s.get("fotos_json") or "[]")
            except: s["fotos_json"] = []

        cursor.execute("SELECT nome FROM usuarios WHERE id = %s", (session["user_id"],))
        usuario = cursor.fetchone()
        nome_corretor = (usuario or {}).get("nome","Corretor")

    except Exception as e:
        print("Erro ao buscar sinistros:", e)
        sinistros_corretor = []
        nome_corretor = "Corretor"
    finally:
        try: cursor.close(); conn.close()
        except: pass

    return render_template(
        "sinistros_corretor.html",
        sinistros_corretor=sinistros_corretor,
        corretor_nome=nome_corretor
    )

# ------------------------------------
# Criar / Atualizar
# ------------------------------------
@app.route("/adicionar_sinistro", methods=["POST"])
def adicionar_sinistro():
    if "user_id" not in session or session.get("user_type") != "Corretor":
        flash("Acesso não autorizado!", "danger")
        return redirect(url_for("corretor_login"))

    cliente          = request.form.get("cliente")
    cpf_cliente      = request.form.get("cpf_cliente")
    numero_apolice   = request.form.get("numero_apolice")
    seguradora       = request.form.get("seguradora")
    valor_estimado   = request.form.get("valor_estimado")
    local_ocorrencia = request.form.get("local")
    data_ocorrencia  = request.form.get("data_ocorrencia")
    tipo             = request.form.get("tipo")
    descricao        = request.form.get("descricao")
    anotacoes        = request.form.get("anotacoes")
    status           = request.form.get("status")
    corretor_id      = session["user_id"]

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 1) insere o sinistro (sem anexos ainda)
        cursor.execute("""
            INSERT INTO sinistros
                (cliente, cpf_cliente, numero_apolice, seguradora, valor_estimado, `local`,
                 data_ocorrencia, tipo, descricao, anotacoes, status, corretor_id,
                 documentos_json, fotos_json)
            VALUES
                (%s, %s, %s, %s, %s, %s,
                 %s, %s, %s, %s, %s, %s,
                 %s, %s)
        """, (cliente, cpf_cliente, numero_apolice, seguradora, valor_estimado, local_ocorrencia,
              data_ocorrencia, tipo, descricao, anotacoes, status, corretor_id,
              None, None))
        conn.commit()

        sinistro_id = cursor.lastrowid

        # 2) salva arquivos no disco (padrão igual Propostas)
        base_dir = os.path.join(UPLOAD_BASE_SIN, str(sinistro_id))
        docs_dir = os.path.join(base_dir, "documentos")
        imgs_dir = os.path.join(base_dir, "fotos")
        _ensure_dir(docs_dir)
        _ensure_dir(imgs_dir)

        documentos_paths = []
        fotos_paths = []

        # aceita "documentos[]", "documentos", "documentos_sinistro"
        doc_files = []
        for k in ("documentos[]", "documentos", "documentos_sinistro"):
            doc_files.extend(request.files.getlist(k))
        for f in doc_files:
            if not f or not f.filename or not _ext_ok(f.filename, ALLOWED_DOCS):
                continue
            fname = _unique_name(f.filename)
            full_path = os.path.join(docs_dir, fname)
            f.save(full_path)
            url_rel = os.path.join('static','uploads','sinistros', str(sinistro_id), 'documentos', fname).replace('\\','/')
            documentos_paths.append(url_rel)

        # aceita "fotos[]", "fotos", "fotos_sinistro"
        foto_files = []
        for k in ("fotos[]", "fotos", "fotos_sinistro"):
            foto_files.extend(request.files.getlist(k))
        for f in foto_files:
            if not f or not f.filename or not _ext_ok(f.filename, ALLOWED_IMGS):
                continue
            fname = _unique_name(f.filename)
            full_path = os.path.join(imgs_dir, fname)
            f.save(full_path)
            url_rel = os.path.join('static','uploads','sinistros', str(sinistro_id), 'fotos', fname).replace('\\','/')
            fotos_paths.append(url_rel)

        documentos_json = json.dumps(documentos_paths, ensure_ascii=False) if documentos_paths else None
        fotos_json      = json.dumps(fotos_paths, ensure_ascii=False)      if fotos_paths else None

        cursor.execute("""
            UPDATE sinistros
               SET documentos_json = %s,
                   fotos_json      = %s
             WHERE id = %s
        """, (documentos_json, fotos_json, sinistro_id))
        conn.commit()

        msg = "Sinistro cadastrado com sucesso!"
        if (documentos_paths or fotos_paths):
            msg += f" ({len(documentos_paths)} documento(s), {len(fotos_paths)} foto(s) anexados)"
        flash(msg, "success")

    except Exception as e:
        print("Erro ao inserir sinistro / salvar uploads:", e)
        try: conn.rollback()
        except: pass
        flash("Erro ao cadastrar sinistro.", "danger")
    finally:
        try: cursor.close(); conn.close()
        except: pass

    return redirect(url_for("sinistros"))


@app.route("/atualizar_sinistro", methods=["POST"])
def atualizar_sinistro():
    if "user_id" not in session or session.get("user_type") != "Corretor":
        flash("Acesso não autorizado!", "danger")
        return redirect(url_for("corretor_login"))

    # -------- campos do formulário --------
    sinistro_id      = request.form.get("id_sinistro")
    cliente          = request.form.get("cliente")
    cpf_cliente      = request.form.get("cpf_cliente")
    numero_apolice   = request.form.get("numero_apolice")
    seguradora       = request.form.get("seguradora")
    valor_estimado   = request.form.get("valor_estimado")
    local_ocorrencia = request.form.get("local")
    data_ocorrencia  = request.form.get("data_ocorrencia")
    tipo             = request.form.get("tipo")
    descricao        = request.form.get("descricao")
    anotacoes        = request.form.get("anotacoes")
    status           = request.form.get("status")

    # HIDDENs (iguais aos de Propostas)
    existing_docs_json  = request.form.get("existing_documentos_json") or "[]"
    existing_fotos_json = request.form.get("existing_fotos_json") or "[]"
    remove_docs_json    = request.form.get("remove_documentos_json") or "[]"
    remove_fotos_json   = request.form.get("remove_fotos_json") or "[]"

    try: existing_docs_form  = json.loads(existing_docs_json)
    except: existing_docs_form = []
    try: existing_fotos_form = json.loads(existing_fotos_json)
    except: existing_fotos_form = []
    try: remove_docs_form    = json.loads(remove_docs_json)
    except: remove_docs_form = []
    try: remove_fotos_form   = json.loads(remove_fotos_json)
    except: remove_fotos_form = []

    remove_docs_set  = _to_remove_set(remove_docs_form)
    remove_fotos_set = _to_remove_set(remove_fotos_form)

    add_docs = 0
    add_fotos = 0

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 1) Atualiza a tabela principal
        cursor.execute("""
            UPDATE sinistros
               SET cliente=%s,
                   cpf_cliente=%s,
                   numero_apolice=%s,
                   seguradora=%s,
                   valor_estimado=%s,
                   `local`=%s,
                   data_ocorrencia=%s,
                   tipo=%s,
                   descricao=%s,
                   anotacoes=%s,
                   status=%s
             WHERE id=%s
        """, (cliente, cpf_cliente, numero_apolice, seguradora, valor_estimado,
              local_ocorrencia, data_ocorrencia, tipo, descricao, anotacoes, status, sinistro_id))

        # 2) Lê o que já está no BD
        cursor.execute("SELECT documentos_json, fotos_json FROM sinistros WHERE id=%s", (sinistro_id,))
        row = cursor.fetchone()
        antigos_docs_db  = []
        antigos_fotos_db = []
        if row:
            try: antigos_docs_db  = json.loads(row[0]) if row[0] else []
            except: antigos_docs_db = []
            try: antigos_fotos_db = json.loads(row[1]) if row[1] else []
            except: antigos_fotos_db = []

        antigos_docs_db  = _dedupe_by_path(_as_file_objects(antigos_docs_db))
        antigos_fotos_db = _dedupe_by_path(_as_file_objects(antigos_fotos_db))
        existentes_docs  = _dedupe_by_path(_as_file_objects(existing_docs_form))
        existentes_fotos = _dedupe_by_path(_as_file_objects(existing_fotos_form))

        # Base = união (BD + form)
        base_docs  = _dedupe_by_path(antigos_docs_db + existentes_docs)
        base_fotos = _dedupe_by_path(antigos_fotos_db + existentes_fotos)

        # aplica remoções
        if remove_docs_set:
            base_docs  = [d for d in base_docs  if _norm_path(d.get("path")) not in remove_docs_set]
        if remove_fotos_set:
            base_fotos = [f for f in base_fotos if _norm_path(f.get("path")) not in remove_fotos_set]

        # 3) Salva novos anexos
        base_dir = os.path.join(UPLOAD_BASE_SIN, str(sinistro_id))
        docs_dir = os.path.join(base_dir, "documentos")
        imgs_dir = os.path.join(base_dir, "fotos")
        _ensure_dir(docs_dir); _ensure_dir(imgs_dir)

        novos_docs_objs = []
        doc_files = []
        for k in ("documentos[]", "documentos", "documentos_sinistro"):
            doc_files.extend(request.files.getlist(k))
        for f in doc_files:
            if not f or not f.filename or not _ext_ok(f.filename, ALLOWED_DOCS):
                continue
            fname = _unique_name(f.filename)
            full_path = os.path.join(docs_dir, fname)
            f.save(full_path)
            url_rel = os.path.join("static","uploads","sinistros", str(sinistro_id), "documentos", fname).replace("\\", "/")
            size = None
            try: size = os.path.getsize(full_path)
            except: pass
            novos_docs_objs.append({"original": f.filename, "path": _norm_path(url_rel), "mimetype": f.mimetype, "size": size})
            add_docs += 1

        novos_fotos_objs = []
        foto_files = []
        for k in ("fotos[]", "fotos", "fotos_sinistro"):
            foto_files.extend(request.files.getlist(k))
        for f in foto_files:
            if not f or not f.filename or not _ext_ok(f.filename, ALLOWED_IMGS):
                continue
            fname = _unique_name(f.filename)
            full_path = os.path.join(imgs_dir, fname)
            f.save(full_path)
            url_rel = os.path.join("static","uploads","sinistros", str(sinistro_id), "fotos", fname).replace("\\", "/")
            size = None
            try: size = os.path.getsize(full_path)
            except: pass
            novos_fotos_objs.append({"original": f.filename, "path": _norm_path(url_rel), "mimetype": f.mimetype, "size": size})
            add_fotos += 1

        docs_final  = _dedupe_by_path(base_docs  + novos_docs_objs)
        fotos_final = _dedupe_by_path(base_fotos + novos_fotos_objs)

        # (opcional) remover fisicamente arquivos deletados
        def _try_delete(rel_norm):
            try:
                abs_path = os.path.join(os.path.dirname(__file__), rel_norm)  # rel ao projeto
                if os.path.isfile(abs_path):
                    os.remove(abs_path)
            except Exception:
                pass

        for it in antigos_docs_db:
            p = _norm_path(it.get("path"))
            if p in remove_docs_set:
                _try_delete(p)
        for it in antigos_fotos_db:
            p = _norm_path(it.get("path"))
            if p in remove_fotos_set:
                _try_delete(p)

        cursor.execute("""
            UPDATE sinistros
               SET documentos_json = %s,
                   fotos_json      = %s
             WHERE id = %s
        """, (json.dumps(docs_final, ensure_ascii=False) if docs_final else None,
              json.dumps(fotos_final, ensure_ascii=False) if fotos_final else None,
              sinistro_id))

        conn.commit()

        if add_docs or add_fotos or remove_docs_set or remove_fotos_set:
            msg = "✅ Sinistro atualizado."
            if add_docs or add_fotos:
                msg += f" Novos anexos: {add_docs} doc(s), {add_fotos} foto(s)."
            if remove_docs_set or remove_fotos_set:
                msg += f" Removidos: {len(remove_docs_set)} doc(s), {len(remove_fotos_set)} foto(s)."
            flash(msg, "success")
        else:
            flash("✅ Sinistro atualizado com sucesso!", "success")

    except Exception as e:
        import traceback
        print("\n" + "="*70)
        print("❌ ERRO AO ATUALIZAR SINISTRO:")
        print("Tipo:", type(e))
        print("Mensagem:", e)
        traceback.print_exc()
        print("="*70 + "\n")
        try: conn.rollback()
        except: pass
        flash("Erro ao atualizar sinistro.", "danger")
    finally:
        try: cursor.close(); conn.close()
        except: pass

    return redirect(url_for("sinistros"))


@app.route("/excluir_sinistro", methods=["POST"])
def excluir_sinistro():
    if "user_id" not in session:
        return redirect(url_for("corretor_login"))

    id_sinistro = request.form.get("id_sinistro")

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 🔸 Primeiro, exclui o registro vinculado na tabela sinistros_segurado
        cursor.execute("DELETE FROM sinistros_segurado WHERE sinistro_id = %s", (id_sinistro,))

        # 🔸 Depois, exclui o registro da tabela principal sinistros
        cursor.execute("DELETE FROM sinistros WHERE id = %s", (id_sinistro,))

        conn.commit()

    except Exception as e:
        conn.rollback()
        print(f"Erro ao excluir sinistro: {e}")

    finally:
        cursor.close()
        conn.close()

    return redirect(url_for("sinistros"))


# ---------- Função utilitária para conversão de datas ----------
def parse_date_string_to_iso(date_str):
    """
    Recebe uma string de data em DD/MM/YYYY ou YYYY-MM-DD (ou DD-MM-YYYY)
    e retorna 'YYYY-MM-DD'. Lança ValueError se não conseguir parsear.
    """
    if not date_str:
        raise ValueError("Data vazia")

    s = str(date_str).strip()

    # dd/mm/yyyy
    if '/' in s:
        return datetime.strptime(s, '%d/%m/%Y').date().strftime('%Y-%m-%d')

    # yyyy-mm-dd (ISO) ou dd-mm-yyyy
    if '-' in s:
        try:
            return datetime.strptime(s, '%Y-%m-%d').date().strftime('%Y-%m-%d')
        except ValueError:
            return datetime.strptime(s, '%d-%m-%Y').date().strftime('%Y-%m-%d')

    raise ValueError("Formato de data desconhecido")

# ---------- ROTAS DO CALENDÁRIO ----------

@app.route("/calendario_corretor.html")
def calendario():
    if "user_id" not in session or session.get("user_type") != "Corretor":
        return redirect(url_for("corretor_login"))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT nome FROM usuarios WHERE id = %s", (session["user_id"],))
    usuario = cursor.fetchone()
    cursor.close()
    conn.close()
    
    nome_corretor = usuario["nome"] if usuario else "Corretor"

    return render_template("calendario_corretor.html", corretor_nome=nome_corretor)

@app.route("/api/compromissos", methods=["GET"])
def get_compromissos():
    # garanta que só o corretor logado acesse seus próprios compromissos
    if "user_id" not in session or session.get("user_type") != "Corretor":
        return jsonify({"error": "Acesso não autorizado"}), 401

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Traga os campos crus (date/time como tipos nativos) e formate em Python
    cursor.execute("""
        SELECT
            id,
            titulo,
            cliente,
            telefone,
            email,
            tipo_seguro,
            status,
            data,
            horario,
            observacoes
        FROM compromissos
        WHERE corretor_id = %s
        ORDER BY data, horario
    """, (session["user_id"],))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    def to_date_str(d):
        # aceita date/datetime ou string; devolve 'YYYY-MM-DD'
        if d is None:
            return None
        return d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else str(d)[:10]

    def to_time_str(t):
        # aceita time/datetime ou string; devolve 'HH:MM'
        if t is None:
            return None
        return t.strftime("%H:%M") if hasattr(t, "strftime") else str(t)[:5]

    out = []
    for r in rows:
        out.append({
            "id": r["id"],
            "title": r["titulo"],
            "client": r["cliente"],
            "phone": r["telefone"],
            "email": r["email"],
            "insuranceType": r["tipo_seguro"],
            "status": r["status"],
            "date": to_date_str(r["data"]),       # <- '2025-10-07'
            "time": to_time_str(r["horario"]),    # <- '13:00'
            "notes": r["observacoes"],
        })

    return jsonify(out)



@app.route("/api/compromissos/proximos", methods=["GET"])
def get_proximos_compromissos():
    if "user_id" not in session or session.get("user_type") != "Corretor":
        return jsonify({"error": "Acesso não autorizado"}), 401

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT id, 
                   titulo AS title, 
                       status,
                       telefone AS phone,
                   cliente AS client, 
                   DATE_FORMAT(data, '%d/%m/%Y') AS formatted_date, 
                   TIME_FORMAT(horario, '%H:%i') AS time,
                   observacoes AS notes
            FROM compromissos
            WHERE corretor_id = %s AND data >= CURDATE()
            ORDER BY data, horario
            LIMIT 10
        """, (session["user_id"],))

        compromissos = cursor.fetchall()
        return jsonify(compromissos)

    except Exception as e:
        print(f"Erro ao buscar próximos compromissos: {str(e)}")
        return jsonify({"error": str(e)}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

@app.route("/api/compromissos", methods=["POST"])
def add_compromisso():
    if "user_id" not in session or session.get("user_type") != "Corretor":
        return jsonify({"error": "Acesso não autorizado"}), 401

    dados = request.get_json()

    try:
        try:
            data_iso = parse_date_string_to_iso(dados.get("date", ""))
        except ValueError:
            return jsonify({"error": "Formato de data inválido. Use DD/MM/YYYY ou YYYY-MM-DD"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO compromissos (
                titulo, cliente, telefone, email, tipo_seguro, status, 
                data, horario, observacoes, corretor_id
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            dados["title"],
            dados["client"],
            dados.get("phone", ""),
            dados.get("email", ""),
            dados.get("insuranceType", ""),
            dados.get("status", "pending"),
            data_iso,
            dados.get("time", "09:00"),
            dados.get("notes", ""),
            session["user_id"]
        ))

        conn.commit()
        return jsonify({"success": True, "id": cursor.lastrowid})
    except Exception as e:
        print(f"Erro ao adicionar compromisso: {str(e)}")
        return jsonify({"error": str(e)}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

@app.route("/api/compromissos/<int:id>", methods=["GET"])
def get_compromisso(id):
    if "user_id" not in session or session.get("user_type") != "Corretor":
        return jsonify({"error": "Acesso não autorizado"}), 401

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT id, 
                   titulo AS title, 
                   cliente AS client, 
                   telefone AS phone,
                   email,
                   tipo_seguro AS insuranceType,
                   status,
                   DATE_FORMAT(data, '%%Y-%%m-%%d') AS date,
                   TIME_FORMAT(horario, '%%H:%%i') AS time,
                   observacoes AS notes
            FROM compromissos
            WHERE id = %s AND corretor_id = %s
        """, (id, session["user_id"]))

        compromisso = cursor.fetchone()
        
        if not compromisso:
            return jsonify({"error": "Compromisso não encontrado"}), 404
            
        return jsonify(compromisso)
    except Exception as e:
        print(f"Erro ao buscar compromisso: {str(e)}")
        return jsonify({"error": str(e)}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

@app.route("/api/compromissos/<int:id>", methods=["PUT"])
def update_compromisso(id):
    if "user_id" not in session or session.get("user_type") != "Corretor":
        return jsonify({"error": "Acesso não autorizado"}), 401

    dados = request.get_json()

    try:
        try:
            data_iso = parse_date_string_to_iso(dados.get("date", ""))
        except ValueError:
            return jsonify({"error": "Formato de data inválido. Use DD/MM/YYYY ou YYYY-MM-DD"}), 400

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT id FROM compromissos WHERE id = %s AND corretor_id = %s",
                       (id, session["user_id"]))
        if not cursor.fetchone():
            return jsonify({"error": "Compromisso não encontrado ou não pertence ao usuário"}), 404

        cursor.execute("""
            UPDATE compromissos SET
                titulo = %s,
                cliente = %s,
                telefone = %s,
                email = %s,
                tipo_seguro = %s,
                status = %s,
                data = %s,
                horario = %s,
                observacoes = %s
            WHERE id = %s
        """, (
            dados["title"],
            dados["client"],
            dados.get("phone", ""),
            dados.get("email", ""),
            dados.get("insuranceType", ""),
            dados.get("status", "pending"),
            data_iso,
            dados.get("time", "09:00"),
            dados.get("notes", ""),
            id
        ))

        conn.commit()
        return jsonify({"success": True})
    except Exception as e:
        print(f"Erro ao atualizar compromisso: {str(e)}")
        return jsonify({"error": str(e)}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()


@app.route("/api/compromissos/<int:id>", methods=["DELETE"])
def delete_compromisso(id):
    if "user_id" not in session or session.get("user_type") != "Corretor":
        return jsonify({"error": "Acesso não autorizado"}), 401

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM compromissos WHERE id = %s AND corretor_id = %s",
                       (id, session["user_id"]))

        if cursor.rowcount == 0:
            return jsonify({"error": "Compromisso não encontrado ou não pertence ao usuário"}), 404

        conn.commit()
        return jsonify({"success": True})
    except Exception as e:
        print(f"Erro ao excluir compromisso: {str(e)}")
        return jsonify({"error": str(e)}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

@app.route("/editar_apolice/<int:id>", methods=["POST"])
def editar_apolice(id):
    if "user_id" not in session or session.get("user_type") != "Corretor":
        flash("Acesso não autorizado!", "danger")
        return redirect(url_for("corretor_login"))

    try:
        # Coletar dados do formulário
        nome = request.form.get("nome")
        tipo_pessoa = request.form.get("tipo_pessoa")
        cpf_cnpj = request.form.get("cpf_cnpj")
        email = request.form.get("email")
        telefone = request.form.get("telefone")
        nome_fantasia = request.form.get("nome_fantasia")
        rg_inscricao = request.form.get("rg_inscricao")
        endereco_completo = request.form.get("endereco")  # Endereço + número
        bairro = request.form.get("bairro")
        cidade = request.form.get("cidade")
        estado = request.form.get("estado")
        tipo_apolice = request.form.get("tipo_apolice")
        valor_apolice = request.form.get("valor_apolice")
        data_inicio = request.form.get("data_inicio")
        data_termino = request.form.get("data_termino")
        cor = request.form.get("cor")
        ano_modelo = request.form.get("ano_modelo")
        status = request.form.get("status")
        observacoes = request.form.get("observacoes")

        # Separar endereço e número (se necessário)
        endereco, numero = endereco_completo.rsplit(" - ", 1) if " - " in endereco_completo else (endereco_completo, "")

        # Conectar ao banco de dados
        conn = get_db_connection()
        cursor = conn.cursor()

        # Atualizar a apólice na tabela clientes_corretor
        cursor.execute("""
            UPDATE clientes_corretor
            SET nome = %s, tipo_pessoa = %s, cpf_cnpj = %s, email = %s, telefone = %s,
                nome_fantasia = %s, rg_inscricao = %s, endereco = %s, numero = %s,
                bairro = %s, cidade = %s, estado = %s, tipo_apolice = %s,
                valor_apolice = %s, data_inicio = %s, data_termino = %s,
                cor = %s, ano_modelo = %s, status = %s, observacoes = %s
            WHERE id = %s
        """, (
            nome, tipo_pessoa, cpf_cnpj, email, telefone, nome_fantasia, rg_inscricao,
            endereco, numero, bairro, cidade, estado, tipo_apolice, valor_apolice,
            data_inicio, data_termino, cor, ano_modelo, status, observacoes, id
        ))

        conn.commit()
        flash("Apólice atualizada com sucesso!", "success")

    except Exception as e:
        print("Erro ao atualizar apólice:", e)
        flash("Erro ao atualizar apólice. Verifique os dados e tente novamente.", "danger")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for("detalhes_cliente", id=id))

@app.route("/excluir_apolice/<int:id>", methods=["POST"])
def excluir_apolice(id):
    if "user_id" not in session or session.get("user_type") != "Corretor":
        flash("Acesso não autorizado!", "danger")
        return redirect(url_for("corretor_login"))

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Exclui SOMENTE a apólice do corretor logado
        cur.execute("""
            DELETE FROM apolices
             WHERE id = %s AND corretor_id = %s
        """, (id, session["user_id"]))

        if cur.rowcount == 0:
            # não encontrou a apólice (ou não pertence a este corretor)
            flash("Apólice não encontrada ou sem permissão para excluir.", "warning")
        else:
            conn.commit()
            flash("Apólice excluída com sucesso!", "success")

    except Exception as e:
        msg = str(e)
        # 1451 = foreign key constraint (há vínculos, não pode excluir)
        if "1451" in msg:
            flash("Não foi possível excluir: existem vínculos com esta apólice (ex.: sinistros/parcelas).", "warning")
        else:
            print("Erro ao excluir apólice:", e)
            flash("Erro ao excluir apólice.", "danger")
    finally:
        try:
            cur.close(); conn.close()
        except:
            pass

    return redirect(url_for("apolices"))


# 🔹 Rota para clientes recentes do corretor logado (JSON)
@app.route("/api/corretor/clientes-recentes", methods=["GET"])
def clientes_recentes_corretor():
    if "user_id" not in session or session.get("user_type") != "Corretor":
        return jsonify({"erro": "Acesso não autorizado"}), 403

    try:
        corretor_id = session.get("user_id")
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT 
                nome,
                email,
                telefone,
                DATE_FORMAT(CURDATE(), '%d/%m/%Y') AS data_cadastro,
                tipo_seguro AS apolices,
                status 
            FROM clientes_corretor
            WHERE corretor_id = %s
            ORDER BY id DESC
            LIMIT 5
        """, (corretor_id,))
        
        clientes = cursor.fetchall()

        cursor.close()
        conn.close()

        return jsonify(clientes)
    
    except Exception as e:
        return jsonify({'erro': str(e)}), 500
    
    # 🔹 Rota para o total de clientes do corretor logado
@app.route("/api/corretor/total-clientes")
def total_clientes_corretor():
    if "user_id" not in session or session.get("user_type") != "Corretor":
        return jsonify({"erro": "Acesso não autorizado"}), 403

    try:
        corretor_id = session.get("user_id")
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = "SELECT COUNT(*) FROM clientes_corretor WHERE corretor_id = %s"
        cursor.execute(query, (corretor_id,))
        total = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        return jsonify({'total': total})
    
    except Exception as e:
        print("Erro ao buscar total de clientes:", e)
        return jsonify({'erro': str(e)}), 500

# 🔹 Rota para apólices ativas do corretor logado
# 🔹 Rota para TOTAL de apólices ativas do corretor logado (tabela: apolices)
@app.route("/api/corretor/apolices-ativas")
def apolices_ativas_corretor():
    if "user_id" not in session or session.get("user_type") != "Corretor":
        return jsonify({"erro": "Acesso não autorizado"}), 403

    corretor_id = session["user_id"]
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Conta por status (Ativa/Ativo)
        query = """
            SELECT COUNT(*)
            FROM apolices
            WHERE corretor_id = %s
              AND (status = 'Ativa' OR status = 'Ativo')
        """
        cursor.execute(query, (corretor_id,))
        total = cursor.fetchone()[0] or 0

        return jsonify({"total": int(total)})

    except Exception as e:
        print("Erro ao buscar apólices ativas:", e)
        return jsonify({"erro": str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

# 🔹 Faturamento do corretor (soma das apólices ATIVAS na tabela apolices)
@app.route("/api/corretor/faturamento-mensal")
def faturamento_mensal_corretor():
    if "user_id" not in session or session.get("user_type") != "Corretor":
        return jsonify({"erro": "Acesso não autorizado"}), 403

    conn = cursor = None
    try:
        corretor_id = session["user_id"]
        conn = get_db_connection()
        cursor = conn.cursor()

        # Soma das apólices ativas do corretor
        sql = """
            SELECT COALESCE(SUM(valor_apolice), 0)
            FROM apolices
            WHERE corretor_id = %s
              AND (status = 'Ativa' OR status = 'Ativo')
        """
        cursor.execute(sql, (corretor_id,))
        total = cursor.fetchone()[0] or 0

        return jsonify({"faturamento": float(total)})

    except Exception as e:
        print("Erro ao buscar faturamento:", e)
        return jsonify({"erro": str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@app.route("/api/corretor/taxa-crescimento")
def taxa_crescimento_corretor():
    if "user_id" not in session or session.get("user_type") != "Corretor":
        return jsonify({"error": "Acesso não autorizado"}), 403

    corretor_id = session["user_id"]
    hoje = date.today()
    atual_ini = hoje - relativedelta(days=6)
    atual_fim = hoje
    ant_ini   = hoje - relativedelta(days=13)
    ant_fim   = hoje - relativedelta(days=7)

    conn = cur = None
    try:
        conn = get_db_connection()
        cur  = conn.cursor(dictionary=True)

        cur.execute("""
            SELECT
              SUM(CASE WHEN DATE(data_inicio) BETWEEN %s AND %s THEN 1 ELSE 0 END) AS atual,
              SUM(CASE WHEN DATE(data_inicio) BETWEEN %s AND %s THEN 1 ELSE 0 END) AS anterior
            FROM apolices
            WHERE corretor_id=%s
              AND status IN ('Ativa','Ativo')
              AND data_inicio IS NOT NULL
        """, (atual_ini, atual_fim, ant_ini, ant_fim, corretor_id))
        row = cur.fetchone() or {"atual":0, "anterior":0}
        atual, anterior = int(row["atual"] or 0), int(row["anterior"] or 0)

        if anterior > 0:
            taxa = ((atual - anterior) / anterior) * 100.0
        else:
            taxa = 100.0 if atual > 0 else 0.0

        return jsonify({"taxa_crescimento": round(taxa, 1)})

    except Exception as e:
        print("Erro em taxa_crescimento_corretor:", e)
        return jsonify({"error": str(e)}), 500
    finally:
        try: cur.close(); conn.close()
        except: pass


from datetime import date
from dateutil.relativedelta import relativedelta
from flask import jsonify, request, session

@app.route("/api/corretor/taxa-crescimento/serie")
def taxa_crescimento_serie():
    if "user_id" not in session or session.get("user_type") != "Corretor":
        return jsonify({"error": "Acesso não autorizado"}), 403

    corretor_id = session["user_id"]
    periodo = request.args.get("periodo", "diario")  # diario | semana | mensal | anual
    hoje = date.today()

    conn = cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)

        # -------------------------------------------------------------
        # 🔹 PERÍODO DIÁRIO
        # -------------------------------------------------------------
        if periodo == "diario":
            H = 7
            inicio = hoje - relativedelta(days=(2 * H - 1))
            cur.execute("""
                SELECT DATE(data_inicio) AS k, COUNT(*) AS total
                FROM apolices
                WHERE corretor_id = %s
                  AND status = 'Ativa'
                  AND data_inicio >= %s
                GROUP BY k
                ORDER BY k ASC
            """, (corretor_id, inicio))
            mapa = {r["k"].strftime("%Y-%m-%d"): int(r["total"]) for r in cur.fetchall()}

            dias = [(inicio + relativedelta(days=i)) for i in range(2 * H)]
            seq = [mapa.get(d.strftime("%Y-%m-%d"), 0) for d in dias]
            prev_seq, curr_seq = seq[:H], seq[H:]
            labels = [d.strftime("%Y-%m-%d") for d in dias[H:]]
            serie = curr_seq

        # -------------------------------------------------------------
        # 🔹 PERÍODO SEMANAL
        # -------------------------------------------------------------
        elif periodo == "semana":
            H = 12
            inicio = hoje - relativedelta(weeks=(2 * H - 1))
            cur.execute("""
                SELECT YEARWEEK(data_inicio, 1) AS k, COUNT(*) AS total
                FROM apolices
                WHERE corretor_id = %s
                  AND status = 'Ativa'
                  AND data_inicio >= %s
                GROUP BY k
                ORDER BY k ASC
            """, (corretor_id, inicio))
            mapa = {str(r["k"]): int(r["total"]) for r in cur.fetchall()}

            weeks = []
            for i in range(2 * H):
                y, w = (hoje - relativedelta(weeks=(2 * H - 1 - i))).isocalendar()[:2]
                weeks.append((y, w, f"{y}{str(w).zfill(2)}"))

            seq = [mapa.get(k, 0) for (_, _, k) in weeks]
            prev_seq, curr_seq = seq[:H], seq[H:]
            labels = [f"{y}-S{w}" for (y, w, _) in weeks[H:]]
            serie = curr_seq

        # -------------------------------------------------------------
        # 🔹 PERÍODO MENSAL (robusto + com override e debug no JSON)
        # -------------------------------------------------------------
        elif periodo == "mensal":
            H = 12  # últimos 12 meses, incluindo o atual

            # 1) Fonte do corretor_id: querystring > sessão
            #    Ex.: /api/.../serie?periodo=mensal&corretor_id=2
            corretor_id_override = request.args.get("corretor_id", type=int)
            cid = corretor_id_override if corretor_id_override is not None else corretor_id

            # 2) Consulta exatamente como no Workbench (intervalo computado pelo MySQL)
            sql = """
                SELECT DATE_FORMAT(data_inicio, '%Y-%m') AS mes, COUNT(*) AS total
                FROM apolices
                WHERE corretor_id = %s
                  AND TRIM(UPPER(status)) IN ('ATIVA','ATIVO')
                  AND data_inicio >= DATE_SUB(CURDATE(), INTERVAL 12 MONTH)
                GROUP BY mes
                ORDER BY mes ASC
            """
            cur.execute(sql, (cid,))
            rows = cur.fetchall() or []

            # 3) Mapa { 'YYYY-MM': total }
            dados = {r["mes"]: int(r["total"]) for r in rows}

            # 4) Gera os 12 meses até o mês atual (YYYY-MM)
            base = date.today().replace(day=1)
            meses = [(base - relativedelta(months=(H - 1 - i))).strftime("%Y-%m") for i in range(H)]

            # 5) Série com zeros nos meses “vazios”
            serie = [dados.get(m, 0) for m in meses]

            # 6) Taxa (último vs penúltimo)
            if len(serie) >= 2 and serie[-2] > 0:
                taxa = ((serie[-1] - serie[-2]) / serie[-2]) * 100.0
            elif serie[-1] > 0:
                taxa = 100.0
            else:
                taxa = 0.0

            # 7) Labels no formato que seu JS espera: "YYYY-MMM" (ex: "2025-M09")
            labels = [f"{m[:4]}-M{m[5:]}" for m in meses]

            # 8) Se pedir ?debug=1, devolve informações extras no próprio JSON
            if request.args.get("debug") == "1":
                return jsonify({
                    "labels": labels,
                    "series": serie,
                    "taxa_crescimento": round(taxa, 1),
                    "_debug": {
                        "corretor_id_usado": cid,
                        "rows": rows,          # [{'mes':'2025-09','total':1}, ...]
                        "mapa": dados,         # {'2025-09':1, ...}
                        "meses_gerados": meses # ['2024-11', ..., '2025-10']
                    }
                })

            return jsonify({
                "labels": labels,
                "series": serie,
                "taxa_crescimento": round(taxa, 1)
            })


        # -------------------------------------------------------------
        # 🔹 PERÍODO ANUAL
        # -------------------------------------------------------------
        elif periodo == "anual":
            H = 4
            inicio = (hoje - relativedelta(years=(2 * H - 1))).replace(month=1, day=1)
            cur.execute("""
                SELECT YEAR(data_inicio) AS k, COUNT(*) AS total
                FROM apolices
                WHERE corretor_id = %s
                  AND status = 'Ativa'
                  AND data_inicio >= %s
                GROUP BY YEAR(data_inicio)
                ORDER BY k ASC
            """, (corretor_id, inicio))
            mapa = {str(r["k"]): int(r["total"]) for r in cur.fetchall()}

            anos = [str((inicio + relativedelta(years=i)).year) for i in range(2 * H)]
            seq = [mapa.get(a, 0) for a in anos]
            prev_seq, curr_seq = seq[:H], seq[H:]
            labels = anos[H:]
            serie = curr_seq

        else:
            return jsonify({"error": "Período inválido"}), 400

        # -------------------------------------------------------------
        # 🔹 TAXA DE CRESCIMENTO FINAL
        # -------------------------------------------------------------
        if periodo != "mensal":  # mensal já calcula acima
            prev_sum = sum(prev_seq)
            curr_sum = sum(curr_seq)
            if prev_sum > 0:
                taxa = ((curr_sum - prev_sum) / prev_sum) * 100.0
            else:
                taxa = 100.0 if curr_sum > 0 else 0.0

        return jsonify({
            "labels": labels,
            "series": serie,
            "taxa_crescimento": round(taxa, 1)
        })

    except Exception as e:
        print("Erro em taxa_crescimento_serie:", e)
        return jsonify({"error": str(e)}), 500
    finally:
        try:
            cur.close(); conn.close()
        except:
            pass


# --- ROTAS: Configurações do Corretor ---
import json
from flask import request, jsonify

# Cria a tabela se não existir
def ensure_config_table():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS corretor_configuracoes (
            corretor_id INT PRIMARY KEY,
            comissao_padrao DECIMAL(5,2) DEFAULT 0.00,
            especializacao VARCHAR(100) DEFAULT NULL,
            regioes JSON NULL,
            tipos_propriedades JSON NULL,
            notif_email TINYINT(1) DEFAULT 1,
            notif_push  TINYINT(1) DEFAULT 0,
            notif_som   TINYINT(1) DEFAULT 1,
            notif_promo TINYINT(1) DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                       ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (corretor_id) REFERENCES usuarios(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)
    conn.commit()
    cur.close()
    conn.close()

def _default_config():
    return {
        "comissao_padrao": 6.0,
        "especializacao": "Residencial e Comercial",
        "regioes": ["São Paulo", "Campinas", "Santos"],
        "tipos_propriedades": ["Apartamento", "Casa", "Comercial"],
        "notificacoes": {"email": True, "push": False, "som": True, "promo": False}
    }

def _row_to_config(row):
    """Converte uma linha do MySQL para o dicionário esperado pelo front."""
    if not row:
        return _default_config()
    # row: (comissao, especializacao, regioes_json, tipos_json, email, push, som, promo)
    regioes = []
    tipos = []
    try:
        regioes = json.loads(row[2]) if row[2] else []
    except Exception:
        regioes = []
    try:
        tipos = json.loads(row[3]) if row[3] else []
    except Exception:
        tipos = []

    return {
        "comissao_padrao": float(row[0] or 0),
        "especializacao": row[1] or "Residencial e Comercial",
        "regioes": regioes,
        "tipos_propriedades": tipos,
        "notificacoes": {
            "email": bool(row[4]),
            "push":  bool(row[5]),
            "som":   bool(row[6]),
            "promo": bool(row[7]),
        }
    }

@app.route("/api/corretor/configuracoes", methods=["GET"])
def get_corretor_config():
    # exige login de Corretor
    if "user_id" not in session or session.get("user_type") != "Corretor":
        return jsonify({"error": "Não autorizado"}), 401

    ensure_config_table()

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT comissao_padrao, especializacao, regioes, tipos_propriedades,
                   notif_email, notif_push, notif_som, notif_promo
            FROM corretor_configuracoes
            WHERE corretor_id = %s
        """, (session["user_id"],))
        row = cur.fetchone()
        cfg = _row_to_config(row)
        return jsonify(cfg)
    except Exception as e:
        print("Erro GET /api/corretor/configuracoes:", e)
        return jsonify(_default_config()), 200  # devolve defaults em caso de falha
    finally:
        cur.close()
        conn.close()

@app.route("/api/corretor/configuracoes", methods=["POST"])
def post_corretor_config():
    # exige login de Corretor
    if "user_id" not in session or session.get("user_type") != "Corretor":
        return jsonify({"error": "Não autorizado"}), 401

    ensure_config_table()

    data = request.get_json(silent=True) or {}
    # normalização / defaults
    comissao = float(data.get("comissao_padrao", 6) or 0)
    if comissao < 0: comissao = 0
    if comissao > 100: comissao = 100

    especializacao = (data.get("especializacao") or "Residencial e Comercial").strip()

    regioes = data.get("regioes") or []
    if isinstance(regioes, str):
        # aceita CSV
        regioes = [r.strip() for r in regioes.split(",") if r.strip()]
    tipos = data.get("tipos_propriedades") or []

    notificacoes = data.get("notificacoes") or {}
    notif_email = 1 if notificacoes.get("email", True) else 0
    notif_push  = 1 if notificacoes.get("push", False) else 0
    notif_som   = 1 if notificacoes.get("som", True) else 0
    notif_promo = 1 if notificacoes.get("promo", False) else 0

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # UPSERT
        cur.execute("""
            INSERT INTO corretor_configuracoes
                (corretor_id, comissao_padrao, especializacao,
                 regioes, tipos_propriedades,
                 notif_email, notif_push, notif_som, notif_promo)
            VALUES
                (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                comissao_padrao = VALUES(comissao_padrao),
                especializacao  = VALUES(especializacao),
                regioes         = VALUES(regioes),
                tipos_propriedades = VALUES(tipos_propriedades),
                notif_email = VALUES(notif_email),
                notif_push  = VALUES(notif_push),
                notif_som   = VALUES(notif_som),
                notif_promo = VALUES(notif_promo)
        """, (
            session["user_id"],
            comissao,
            especializacao,
            json.dumps(regioes, ensure_ascii=False),
            json.dumps(tipos, ensure_ascii=False),
            notif_email, notif_push, notif_som, notif_promo
        ))
        conn.commit()

        # retorna o que ficou salvo
        saved = {
            "comissao_padrao": comissao,
            "especializacao": especializacao,
            "regioes": regioes,
            "tipos_propriedades": tipos,
            "notificacoes": {
                "email": bool(notif_email),
                "push": bool(notif_push),
                "som": bool(notif_som),
                "promo": bool(notif_promo),
            }
        }
        return jsonify({"message": "Configurações salvas com sucesso!", **saved}), 200
    except Exception as e:
        print("Erro POST /api/corretor/configuracoes:", e)
        conn.rollback()
        return jsonify({"error": "Falha ao salvar configurações"}), 500
    finally:
        cur.close()
        conn.close()

# ====== COTAÇÕES – Somente tabela `cotacoes` (compatível com seu schema) ======

COT_STATUS = {"recebida", "em_analise", "enviada_seguradora"}  # igual ao ENUM da tabela

def _fmt_datetime(dt):
    from datetime import datetime, date
    try:
        if isinstance(dt, datetime):
            return dt.strftime("%d/%m/%Y %H:%M")
        if isinstance(dt, date):
            return dt.strftime("%d/%m/%Y")
        return datetime.fromisoformat(str(dt)).strftime("%d/%m/%Y %H:%M")
    except Exception:
        return ""


@app.route("/api/corretor/cotacoes", methods=["GET"])
def api_corretor_cotacoes():
    # precisa estar logado como Corretor
    if "user_id" not in session or session.get("user_type") != "Corretor":
        return jsonify({"error": "Não autorizado"}), 401

    conn = get_db_connection()
    cur  = conn.cursor(dictionary=True)
    try:
        # Somente colunas que EXISTEM no seu schema
        cur.execute("""
            SELECT
                c.id,
                c.tipo,
                c.status,
                c.nome AS cliente_nome,
                c.criado_em
            FROM cotacoes c
            WHERE c.corretor_id = %s
            ORDER BY c.id DESC
        """, (session["user_id"],))

        rows = cur.fetchall() or []

        out = []
        for r in rows:
            out.append({
                "id": r["id"],
                "tipo": r.get("tipo"),
                "status": (r.get("status") or "").lower(),
                "cliente_nome": r.get("cliente_nome"),
                "criado_em_fmt": _fmt_datetime(r.get("criado_em")) if r.get("criado_em") else "",
            })

        return jsonify(out), 200

    except Exception as e:
        print("Erro /api/corretor/cotacoes:", e)
        return jsonify({"error": "Falha ao carregar cotações"}), 500
    finally:
        try: cur.close(); conn.close()
        except: pass


@app.route("/api/corretor/cotacoes/<int:cot_id>", methods=["GET"])
def api_corretor_cotacao_detalhe(cot_id):
    # precisa estar logado como Corretor
    if "user_id" not in session or session.get("user_type") != "Corretor":
        return jsonify({"error": "Não autorizado"}), 401

    conn = get_db_connection()
    cur  = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT *
            FROM cotacoes
            WHERE id = %s
              AND corretor_id = %s
            LIMIT 1
        """, (cot_id, session["user_id"]))
        row = cur.fetchone()
        if not row:
            return jsonify({"error": "Cotação não encontrada"}), 404

        out = {
            "id": row.get("id"),
            "tipo": row.get("tipo"),
            "status": (row.get("status") or "").lower(),
            "cliente_nome": row.get("nome"),
            "email": row.get("email"),
            "telefone": row.get("telefone"),
            "cep": row.get("cep"),
            "cidade": row.get("extra1") if (row.get("extra1") and row.get("extra1").isalpha()) else row.get("extra2"),  # ajuste se você guardar cidade em extra1/extra2
            "observacoes": None,  # não existe no schema; deixe null/None
            "criado_em_fmt": _fmt_datetime(row.get("criado_em")) if row.get("criado_em") else "",
        }
        return jsonify(out), 200

    except Exception as e:
        print("Erro GET /api/corretor/cotacoes/<id>:", e)
        return jsonify({"error": "Falha ao carregar detalhes"}), 500
    finally:
        try: cur.close(); conn.close()
        except: pass

COT_STATUS = {
    "recebida", "em_analise", "enviada_seguradora",
    "respondida", "concluida", "cancelada"
}

@app.route("/api/corretor/cotacoes/<int:cot_id>/status", methods=["PATCH"])
def api_corretor_cotacoes_status(cot_id):
    if "user_id" not in session or session.get("user_type") != "Corretor":
        return jsonify({"ok": False, "error": "Não autorizado"}), 401

    data = request.get_json(silent=True) or {}
    novo_status = (data.get("status") or "").strip().lower()
    if novo_status not in COT_STATUS:
        return jsonify({"ok": False, "error": "Status inválido"}), 400

    conn = get_db_connection()
    cur  = conn.cursor()
    try:
        cur.execute("""
            UPDATE cotacoes
               SET status = %s
             WHERE id = %s
               AND corretor_id = %s
        """, (novo_status, cot_id, session["user_id"]))
        if cur.rowcount == 0:
            return jsonify({"ok": False, "error": "Cotação não encontrada"}), 404

        conn.commit()
        return jsonify({"ok": True}), 200
    except Exception as e:
        conn.rollback()
        print("Erro PATCH /api/corretor/cotacoes/<id>/status:", e)
        return jsonify({"ok": False, "error": "Falha ao atualizar"}), 500
    finally:
        try: cur.close(); conn.close()
        except: pass

# 🔹 Área do Cliente
@app.route("/area_cliente")
def area_cliente():
    if "user_id" not in session or session.get("user_type") != "Segurado":
        flash("Acesso restrito! Faça login como cliente.", "danger")
        return redirect(url_for("cliente_login"))

    user_id = session["user_id"]

    try:
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)

        # 🔹 Dados do usuário logado
        cur.execute("""
            SELECT id, nome, email, telefone, cpf, foto_de_perfil
            FROM usuarios
            WHERE id = %s
        """, (user_id,))
        usuario = cur.fetchone() or {}

        nome_cliente = usuario.get("nome", "Cliente")
        email_cliente = usuario.get("email", "email@exemplo.com")
        telefone_cliente = usuario.get("telefone", "")
        cpf_cliente = usuario.get("cpf")
        foto_cliente = usuario.get("foto_de_perfil")

        # 🔹 Busca apólices do cliente
        cur.execute("""
            SELECT
              id, apolice_id, cliente_id, cliente_nome, cpf,
              numero_apolice, numero_proposta, tipo_apolice, seguradora,
              valor_apolice, data_inicio, data_termino, parcelas,
              primeiro_vencimento, forma_pagamento, observacoes, status,
              enviado_em
            FROM apolices_segurado
            WHERE cliente_id = %s
               OR REPLACE(REPLACE(REPLACE(cpf, '.', ''), '-', ''), ' ', '') =
                  REPLACE(REPLACE(REPLACE(%s, '.', ''), '-', ''), ' ', '')
            ORDER BY id DESC
        """, (user_id, cpf_cliente))
        apolices = cur.fetchall()

        # 🔹 Formatar datas
        for ap in apolices:
            ap["data_inicio_fmt"] = ap["data_inicio"].strftime("%d/%m/%Y") if ap.get("data_inicio") else "-"
            ap["data_termino_fmt"] = ap["data_termino"].strftime("%d/%m/%Y") if ap.get("data_termino") else "-"
            ap["vencimento_fmt"] = ap["primeiro_vencimento"].strftime("%d/%m/%Y") if ap.get("primeiro_vencimento") else "-"

        # ===== KPIs =====
        total_ativas = sum(1 for ap in apolices if (ap.get("status") or "").lower() in ["ativo", "ativa"])
        valor_total = sum(float(ap.get("valor_apolice") or 0) for ap in apolices)

        hoje = date.today()
        vencimentos_proximos = [
            (ap["tipo_apolice"], (ap["primeiro_vencimento"] - hoje).days)
            for ap in apolices
            if ap.get("primeiro_vencimento") and (ap["primeiro_vencimento"] - hoje).days > 0
        ]
        proximo_tipo, dias_vencimento = (vencimentos_proximos[0] if vencimentos_proximos else (None, None))

        # =========================================================
# 🔹 Buscar sinistros do cliente
# =========================================================
        cur.execute("""
        SELECT id, numero_apolice, tipo_sinistro, valor_estimado, status
        FROM sinistros_segurado
        WHERE cliente_id = %s
        OR REPLACE(REPLACE(REPLACE(cpf, '.', ''), '-', ''), ' ', '') =
          REPLACE(REPLACE(REPLACE(%s, '.', ''), '-', ''), ' ', '')
        """, (user_id, cpf_cliente))
        sinistros = cur.fetchall()

        sinistros_abertos = sum(
    1 for s in sinistros if (s.get("status") or "").lower() not in ["concluido", "finalizado"]
)


        kpis = {
            "ativas": total_ativas,
            "valor_total": valor_total,
            "sinistros_abertos": sinistros_abertos,
            "proximo_tipo": proximo_tipo,
            "dias_vencimento": dias_vencimento,
        }

# =========================================================
        # 🔹 Gerar dados para o gráfico "Evolução da Cobertura"
        # =========================================================
        cur.execute("""
            SELECT 
                MONTH(data_inicio) AS mes,
                SUM(valor_apolice) AS total_mes
            FROM apolices_segurado
            WHERE cliente_id = %s
               OR REPLACE(REPLACE(REPLACE(cpf, '.', ''), '-', ''), ' ', '') =
                  REPLACE(REPLACE(REPLACE(%s, '.', ''), '-', ''), ' ', '')
            GROUP BY MONTH(data_inicio)
            ORDER BY mes
        """, (user_id, cpf_cliente))
        grafico_data = cur.fetchall()

        meses_labels = []
        valores_labels = []
        meses_pt = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]

        for row in grafico_data:
            mes_idx = int(row["mes"]) - 1
            meses_labels.append(meses_pt[mes_idx])
            valores_labels.append(float(row["total_mes"] or 0))

        # ===== Foto normalizada =====
        foto_url = None
        if foto_cliente:
            foto_path = str(foto_cliente).replace("\\", "/")
            if foto_path.startswith("http"):
                foto_url = foto_path
            elif foto_path.startswith("static/"):
                foto_url = url_for("static", filename=foto_path.split("static/", 1)[1])
            else:
                foto_url = url_for("static", filename=foto_path)

    except Exception as e:
        print("❌ ERRO AO CARREGAR DADOS DO CLIENTE:", e)
        apolices = []
        kpis = {
            "ativas": 0,
            "valor_total": 0,
            "sinistros_abertos": 0,
            "proximo_tipo": None,
            "dias_vencimento": None,
        }
        foto_url = None

    finally:
        try:
            cur.close()
            conn.close()
        except:
            pass

    return render_template(
        "area_cliente.html",
        cliente_nome=nome_cliente,
        cliente_email=email_cliente,
        cliente_telefone=telefone_cliente,
        cliente_foto=foto_url,
        apolices=apolices,
        sinistros=sinistros,
        grafico_labels=meses_labels,
        grafico_valores=valores_labels,
        kpis=kpis,
        ACTIVE_MENU="dashboard"
    )


# 🔹 Rotas para login e cadastro (cliente e corretor)
@app.route("/cliente_login.html", methods=["GET", "POST"])
def cliente_login():
    if request.method == "POST":
        email = request.form["email"]
        senha = request.form["senha"]

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM usuarios WHERE email = %s AND tipo = 'Segurado'", (email,))
        usuario = cursor.fetchone()
        conn.close()

        if usuario and check_password_hash(usuario["senha_hash"], senha):
            session["user_id"] = usuario["id"]
            session["user_name"] = usuario["nome"]
            session["user_type"] = usuario["tipo"]
            flash("Login realizado com sucesso!", "success")
            return redirect(url_for("area_cliente"))
        else:
            flash("E-mail ou senha inválidos.", "danger")

    return render_template("cliente_login.html")

@app.route("/cliente_cadastro.html", methods=["GET", "POST"])
def cliente_cadastro():
    if request.method == "POST":
        nome = request.form["nome"]
        email = request.form["email"]
        senha = request.form["senha"]
        senha_hash = generate_password_hash(senha)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO usuarios (nome, email, senha_hash, tipo) VALUES (%s, %s, %s, 'Segurado')",
                           (nome, email, senha_hash))
            conn.commit()
            flash("Cadastro realizado com sucesso!", "success")
            return redirect(url_for("cliente_login"))
        except mysql.connector.IntegrityError:
            flash("Este e-mail já está cadastrado.", "danger")
        finally:
            cursor.close()
            conn.close()
    
    return render_template("cliente_cadastro.html")

@app.route("/corretor_login.html", methods=["GET", "POST"])
def corretor_login():
    if request.method == "POST":
        email = request.form["email"]
        senha = request.form["senha"]

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM usuarios WHERE email = %s AND tipo = 'Corretor'", (email,))
        usuario = cursor.fetchone()
        conn.close()

        if usuario and check_password_hash(usuario["senha_hash"], senha):
            session["user_id"] = usuario["id"]
            session["user_name"] = usuario["nome"]
            session["user_type"] = usuario["tipo"]
            flash("Login realizado com sucesso!", "success")
            return redirect(url_for("area_corretor"))
        else:
            flash("E-mail ou senha inválidos.", "danger")

    return render_template("corretor_login.html")

def _parse_date_br(value: str):
    if not value:
        return None
    value = value.strip()
    if not value:
        return None
    # tenta DD/MM/AAAA
    try:
        return datetime.strptime(value, "%d/%m/%Y").date()
    except ValueError:
        pass
    # tenta ISO (AAAA-MM-DD)
    try:
        return datetime.fromisoformat(value).date()
    except Exception:
        return None


@app.route("/dados_cliente.html")
def dadosclientes():
    if "user_id" not in session or session.get("user_type") != "Segurado":
        flash("Acesso restrito! Faça login como cliente.", "danger")
        return redirect(url_for("cliente_login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # 🔹 Dados principais (usuarios)
    cursor.execute("""
        SELECT id, nome, email, telefone, biografia, foto_de_perfil, data_cadastro, cpf, cnpj
        FROM usuarios
        WHERE id = %s
    """, (session["user_id"],))
    cliente = cursor.fetchone()

    # 🔹 Dados adicionais e endereço (meus_dados)
    cursor.execute("""
        SELECT cep, rua, bairro, cidade, estado, complemento,
               estado_civil, nacionalidade, genero, rg, profissao, data_nascimento
        FROM meus_dados
        WHERE usuario_id = %s
    """, (session["user_id"],))
    dados = cursor.fetchone()

    cursor.close()
    conn.close()

    if not cliente:
        flash("Usuário não encontrado.", "danger")
        return redirect(url_for("area_cliente"))

    # 🔑 Passa cliente e dados para o template
    return render_template("dados_cliente.html", cliente=cliente, dados=dados)

@app.route("/api/cliente/pessoais", methods=["POST"])
def api_cliente_pessoais():
    if "user_id" not in session or session.get("user_type") != "Segurado":
        return jsonify({"ok": False, "msg": "Não autorizado"}), 401

    data = request.get_json(silent=True) or {}
    nome = (data.get("nome") or "").strip()
    email = (data.get("email") or "").strip()
    telefone = (data.get("telefone") or "").strip()
    cpf = (data.get("cpf") or "").strip()
    genero = (data.get("genero") or "").strip()

    if not nome or not email:
        return jsonify({"ok": False, "msg": "Nome e e-mail são obrigatórios."}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            UPDATE usuarios
               SET nome=%s, email=%s, telefone=%s, cpf=%s, genero=%s
             WHERE id=%s
        """, (nome, email, telefone, cpf, genero, session["user_id"]))
        conn.commit()
        return jsonify({"ok": True, "msg": "Dados pessoais atualizados."})
    except Exception as e:
        conn.rollback()
        return jsonify({"ok": False, "msg": f"Erro ao atualizar: {e}"}), 500
    finally:
        cursor.close()
        conn.close()

# -----------------------------------------------------------
# API: Atualiza ENDEREÇO (tabela meus_dados)
# Campos: cep, rua, bairro, cidade, estado, complemento
# Faz INSERT se não existir registro para usuario_id; senão UPDATE
# -----------------------------------------------------------
@app.route("/api/cliente/endereco", methods=["POST"])
def api_cliente_endereco():
    if "user_id" not in session or session.get("user_type") != "Segurado":
        return jsonify({"ok": False, "msg": "Não autorizado"}), 401

    data = request.get_json(silent=True) or {}
    cep = (data.get("cep") or "").strip()
    rua = (data.get("rua") or "").strip()
    bairro = (data.get("bairro") or "").strip()
    cidade = (data.get("cidade") or "").strip()
    estado = (data.get("estado") or "").strip()
    complemento = (data.get("complemento") or "").strip()

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # existe registro deste usuario?
        cursor.execute("SELECT id FROM meus_dados WHERE usuario_id=%s", (session["user_id"],))
        row = cursor.fetchone()

        if row:
            cursor.execute("""
                UPDATE meus_dados
                   SET cep=%s, rua=%s, bairro=%s, cidade=%s, estado=%s, complemento=%s
                 WHERE usuario_id=%s
            """, (cep, rua, bairro, cidade, estado, complemento, session["user_id"]))
        else:
            cursor.execute("""
                INSERT INTO meus_dados (usuario_id, cep, rua, bairro, cidade, estado, complemento)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
            """, (session["user_id"], cep, rua, bairro, cidade, estado, complemento))

        conn.commit()
        return jsonify({"ok": True, "msg": "Endereço salvo."})
    except Exception as e:
        conn.rollback()
        return jsonify({"ok": False, "msg": f"Erro ao salvar: {e}"}), 500
    finally:
        cursor.close()
        conn.close()

# -----------------------------------------------------------
# API: Atualiza DADOS ADICIONAIS (tabela meus_dados)
# Campos: estado_civil, nacionalidade, genero_adicional -> genero, rg, profissao, data_nascimento
# INSERT se não existir; UPDATE se existir
# -----------------------------------------------------------
@app.route("/api/cliente/adicionais", methods=["POST"])
def api_cliente_adicionais():
    if "user_id" not in session or session.get("user_type") != "Segurado":
        return jsonify({"ok": False, "msg": "Não autorizado"}), 401

    data = request.get_json(silent=True) or {}
    estado_civil = (data.get("estado_civil") or "").strip()
    nacionalidade = (data.get("nacionalidade") or "").strip()
    genero_adicional = (data.get("genero_adicional") or "").strip()  # guardaremos em meus_dados.genero
    rg = (data.get("rg") or "").strip()
    profissao = (data.get("profissao") or "").strip()
    data_nascimento = _parse_date_br(data.get("data_nascimento"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id FROM meus_dados WHERE usuario_id=%s", (session["user_id"],))
        row = cursor.fetchone()

        if row:
            cursor.execute("""
                UPDATE meus_dados
                   SET estado_civil=%s,
                       nacionalidade=%s,
                       genero=%s,
                       rg=%s,
                       profissao=%s,
                       data_nascimento=%s
                 WHERE usuario_id=%s
            """, (estado_civil, nacionalidade, genero_adicional, rg, profissao, data_nascimento, session["user_id"]))
        else:
            cursor.execute("""
                INSERT INTO meus_dados
                    (usuario_id, estado_civil, nacionalidade, genero, rg, profissao, data_nascimento)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
            """, (session["user_id"], estado_civil, nacionalidade, genero_adicional, rg, profissao, data_nascimento))

        conn.commit()
        return jsonify({"ok": True, "msg": "Dados adicionais salvos."})
    except Exception as e:
        conn.rollback()
        return jsonify({"ok": False, "msg": f"Erro ao salvar: {e}"}), 500
    finally:
        cursor.close()
        conn.close()

# -----------------------------------------------------------
# API: Alterar SENHA (tabela usuarios)
# Espera: senha_atual, nova_senha
# Ajuste o nome da coluna de hash se for diferente de "senha_hash"
# -----------------------------------------------------------
@app.route("/api/cliente/senha", methods=["POST"])
def api_cliente_senha():
    if "user_id" not in session or session.get("user_type") != "Segurado":
        return jsonify({"ok": False, "msg": "Não autorizado"}), 401

    data = request.get_json(silent=True) or {}
    senha_atual = (data.get("senha_atual") or "")
    nova_senha = (data.get("nova_senha") or "")

    if len(nova_senha) < 8:
        return jsonify({"ok": False, "msg": "A nova senha deve ter no mínimo 8 caracteres."}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id, senha_hash FROM usuarios WHERE id=%s", (session["user_id"],))
        row = cursor.fetchone()
        if not row:
            return jsonify({"ok": False, "msg": "Usuário não encontrado."}), 404

        if not check_password_hash(row["senha_hash"], senha_atual):
            return jsonify({"ok": False, "msg": "Senha atual inválida."}), 400

        novo_hash = generate_password_hash(nova_senha)
        cursor.execute("UPDATE usuarios SET senha_hash=%s WHERE id=%s", (novo_hash, session["user_id"]))
        conn.commit()
        return jsonify({"ok": True, "msg": "Senha alterada com sucesso."})
    except Exception as e:
        conn.rollback()
        return jsonify({"ok": False, "msg": f"Erro ao alterar senha: {e}"}), 500
    finally:
        cursor.close()
        conn.close()

# -----------------------------------------------------------
# API: Upload/Remoção de FOTO DE PERFIL (tabela usuarios.foto_de_perfil)
# -----------------------------------------------------------
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
def _allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/api/cliente/foto", methods=["POST"])
def api_cliente_foto():
    if "user_id" not in session or session.get("user_type") != "Segurado":
        return jsonify({"ok": False, "msg": "Não autorizado"}), 401

    file = request.files.get("foto")
    if not file or file.filename == "":
        return jsonify({"ok": False, "msg": "Nenhum arquivo enviado."}), 400
    if not _allowed_file(file.filename):
        return jsonify({"ok": False, "msg": "Extensão não permitida."}), 400

    filename = secure_filename(file.filename)
    ext = filename.rsplit(".", 1)[1].lower()
    new_name = f"user_{session['user_id']}.{ext}"

    upload_dir = os.path.join("static", "uploads", "profile_pics")
    os.makedirs(upload_dir, exist_ok=True)
    save_path = os.path.join(upload_dir, new_name)
    file.save(save_path)

    db_path = os.path.join("static", "uploads", "profile_pics", new_name)

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE usuarios SET foto_de_perfil=%s WHERE id=%s", (db_path, session["user_id"]))
        conn.commit()
        return jsonify({"ok": True, "msg": "Foto atualizada.", "foto_de_perfil": db_path})
    except Exception as e:
        conn.rollback()
        return jsonify({"ok": False, "msg": f"Erro ao salvar foto: {e}"}), 500
    finally:
        cursor.close()
        conn.close()

@app.route("/api/cliente/foto/remover", methods=["POST"])
def api_cliente_foto_remover():
    if "user_id" not in session or session.get("user_type") != "Segurado":
        return jsonify({"ok": False, "msg": "Não autorizado"}), 401

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT foto_de_perfil FROM usuarios WHERE id=%s", (session["user_id"],))
        row = cursor.fetchone()

        if row and row.get("foto_de_perfil"):
            try:
                # tentativa de remover arquivo físico (se existir)
                if os.path.exists(row["foto_de_perfil"]):
                    os.remove(row["foto_de_perfil"])
            except Exception:
                pass

        cursor.execute("UPDATE usuarios SET foto_de_perfil=NULL WHERE id=%s", (session["user_id"],))
        conn.commit()
        return jsonify({"ok": True, "msg": "Foto removida."})
    except Exception as e:
        conn.rollback()
        return jsonify({"ok": False, "msg": f"Erro ao remover foto: {e}"}), 500
    finally:
        cursor.close()
        conn.close()

def _norm_static_path(p: str) -> str | None:
    """Converte caminho para usar com url_for('static', filename=...)."""
    if not p:
        return None
    p = str(p).replace("\\", "/").lstrip("/")
    # se vier 'static/...' mantemos apenas o trecho após 'static/'
    if p.startswith("static/"):
        p = p[len("static/"):]
    return p

def _fmt_dt(dt):
    try:
        if isinstance(dt, str):
            return datetime.fromisoformat(dt).strftime("%d/%m/%Y %H:%M")
        return dt.strftime("%d/%m/%Y %H:%M") if dt else ""
    except Exception:
        return str(dt)[:16]

@app.route("/cotacoes_clientes")
def cotacoes_clientes():
    # precisa estar logado como Segurado
    if "user_id" not in session or session.get("user_type") != "Segurado":
        flash("Acesso restrito! Faça login como cliente.", "danger")
        return redirect(url_for("cliente_login"))

    user_id = session["user_id"]

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    # Dados do cliente logado (nome/foto do topo)
    cur.execute("""
        SELECT id, nome, foto_de_perfil
        FROM usuarios
        WHERE id = %s
    """, (user_id,))
    user = cur.fetchone()

    # Corretores
    cur.execute("""
        SELECT id, nome, email, telefone, foto_de_perfil
        FROM usuarios
        WHERE tipo = 'Corretor'
        ORDER BY nome
    """)
    rows_corr = cur.fetchall() or []

    # ====== Cotações do cliente (para o acompanhamento) ======
    cur.execute("""
        SELECT c.id, c.tipo, c.status, c.token, c.criado_em,
               u.nome AS corretor_nome, u.telefone AS corretor_telefone
        FROM cotacoes c
        LEFT JOIN usuarios u ON u.id = c.corretor_id
        WHERE c.cliente_id = %s
        ORDER BY c.criado_em DESC
        LIMIT 50
    """, (user_id,))
    rows_cot = cur.fetchall() or []

    cur.close(); conn.close()

    # ===== Helpers =====
    def _norm_static_path(p: str | None) -> str | None:
        if not p: return None
        p = str(p).replace("\\", "/").lstrip("/")
        if p.startswith("static/"):
            p = p[len("static/"):]
        return p

    def _normalize_status(status: str) -> str:
       if not status:
        return "recebida"
       s = status.strip().lower()
    # remove acentos
       import unicodedata
       s = "".join(c for c in unicodedata.normalize("NFD", s)
                if unicodedata.category(c) != "Mn")
    # agora s pode ser "em analise", "em análise", "analise"
       if "analise" in s:
        return "em_analise"
       if "enviad" in s:
        return "enviada"
        return "recebida"


    # Monta lista de corretores
    corretores = [{
        "id": r.get("id"),
        "nome": r.get("nome"),
        "email": r.get("email"),
        "telefone": r.get("telefone"),
        "foto": _norm_static_path(r.get("foto_de_perfil")),
    } for r in rows_corr]

    # Monta lista de cotações
    cotacoes_recentes = [{
        "id": r["id"],
        "tipo": r.get("tipo") or "—",
        "status": _normalize_status(r.get("status")),
        "token": r.get("token") or f"SV-{datetime.now().year}-{int(r['id']):06d}",
        "criado_em": _fmt_dt(r.get("criado_em")),
        "corretor_nome": r.get("corretor_nome") or "A definir",
        "corretor_telefone": r.get("corretor_telefone"),
    } for r in rows_cot]

    cliente_nome = (user or {}).get("nome") if user else None
    cliente_foto = _norm_static_path((user or {}).get("foto_de_perfil")) if user else None

    return render_template(
        "cotacoes_clientes.html",
        cliente_nome=cliente_nome,
        cliente_foto=cliente_foto,
        corretores=corretores,
        cotacoes_recentes=cotacoes_recentes,  # <= ESSENCIAL
        cliente_corretor_id=session.get("cliente_corretor_id")
    )

@app.route("/acompanhamento_pp_cliente.html")
def minhas_propostas():
    # restrição de login
    if "user_id" not in session or session.get("user_type") != "Segurado":
        flash("Acesso restrito! Faça login como cliente.", "danger")
        return redirect(url_for("cliente_login"))

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT nome, foto_de_perfil FROM usuarios WHERE id = %s", (session["user_id"],))
    user = cur.fetchone()
    cur.close()
    conn.close()

    # 🔎 DEBUG
    foto_raw = (user or {}).get("foto_de_perfil") or ""
    print("DEBUG FOTO BANCO:", foto_raw)

    # 🔧 Normaliza o que veio do banco para usar com url_for('static', filename=...)
    def _norm_static_path(p):
        if not p:
            return None
        p = str(p).replace("\\", "/").lstrip("/")
        # se vier como 'static/....', remove o prefixo
        if p.startswith("static/"):
            p = p[len("static/"):]
        return p

    foto_rel = _norm_static_path(foto_raw)  # ex.: 'uploads/profile_pics/user_1.jpg'

    # ✅ Se tiver caminho válido, monta URL; senão, None (cai nas iniciais no template)
    foto_url = url_for("static", filename=foto_rel) if foto_rel else None

    return render_template("acompanhamento_pp_cliente.html", user=user, foto_url=foto_url)

@app.route("/acompanhamento_sn_cliente.html")
def sinistros_clientes():
    # restrição de login
    if "user_id" not in session or session.get("user_type") != "Segurado":
        flash("Acesso restrito! Faça login como cliente.", "danger")
        return redirect(url_for("cliente_login"))

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT nome, foto_de_perfil FROM usuarios WHERE id = %s", (session["user_id"],))
    user = cur.fetchone()
    cur.close()
    conn.close()

    # 🔎 DEBUG
    foto_raw = (user or {}).get("foto_de_perfil") or ""
    print("DEBUG FOTO BANCO:", foto_raw)

    # 🔧 Normaliza o que veio do banco para usar com url_for('static', filename=...)
    def _norm_static_path(p):
        if not p:
            return None
        p = str(p).replace("\\", "/").lstrip("/")
        # se vier como 'static/....', remove o prefixo
        if p.startswith("static/"):
            p = p[len("static/"):]
        return p

    foto_rel = _norm_static_path(foto_raw)  # ex.: 'uploads/profile_pics/user_1.jpg'

    # ✅ Se tiver caminho válido, monta URL; senão, None (cai nas iniciais no template)
    foto_url = url_for("static", filename=foto_rel) if foto_rel else None

    return render_template("acompanhamento_sn_cliente.html", user=user, foto_url=foto_url)


# Evita confusão: se alguém entrar em /cotacoes_clientes.html, redireciona para a rota correta
@app.route("/cotacoes_clientes.html")
def cotacoes_clientes_html():
    return redirect(url_for("cotacoes_clientes"))

@app.route("/cotacoes", methods=["POST"], endpoint="criar_cotacao")
def criar_cotacao():
    return redirect(url_for("cotacoes_clientes"))

# ============================================================================
# Helper: cria/pega cliente por e-mail (tolerante ao schema de 'usuarios')
# ============================================================================
def get_or_create_cliente_by_email(email: str, nome: str = "", telefone: str = "") -> int:
    """
    Retorna id do cliente pelo e-mail. Se não existir, cria um registro mínimo na
    tabela 'usuarios' usando apenas as colunas que realmente existem.
    """
    conn = get_db_connection()
    cur  = conn.cursor(dictionary=True)
    try:
        # Quais colunas existem?
        cur.execute("SHOW COLUMNS FROM usuarios")
        cols = {row["Field"] for row in cur.fetchall()}

        # Precisa ter email
        if "email" not in cols:
            raise RuntimeError("A tabela 'usuarios' não possui coluna 'email'.")

        # Procura pelo e-mail (sem filtrar por 'tipo' para não depender do schema)
        cur.execute("SELECT id FROM usuarios WHERE LOWER(email)=LOWER(%s) LIMIT 1", (email,))
        row = cur.fetchone()
        if row:
            return int(row["id"])

        # Monta INSERT apenas com colunas existentes
        insert_cols = []
        insert_vals = []

        if "nome" in cols:
            insert_cols.append("nome"); insert_vals.append(nome or email.split("@")[0])
        if "email" in cols:
            insert_cols.append("email"); insert_vals.append(email)
        if "telefone" in cols:
            insert_cols.append("telefone"); insert_vals.append(telefone)
        if "tipo" in cols:
            insert_cols.append("tipo"); insert_vals.append("Cliente")

        if not insert_cols:
            raise RuntimeError("Não há colunas compatíveis para inserir novo usuário.")

        sql = f"INSERT INTO usuarios ({', '.join(insert_cols)}) VALUES ({', '.join(['%s']*len(insert_cols))})"
        cur2 = conn.cursor()
        try:
            cur2.execute(sql, tuple(insert_vals))
            new_id = cur2.lastrowid
            conn.commit()
            cur2.close()
            return int(new_id)
        except Exception as ie:
            # Pode ser UNIQUE no email. Tenta buscar novamente:
            conn.rollback()
            cur2.close()
            try:
                cur.execute("SELECT id FROM usuarios WHERE LOWER(email)=LOWER(%s) LIMIT 1", (email,))
                row2 = cur.fetchone()
                if row2:
                    return int(row2["id"])
            except:
                pass
            print("INSERT usuarios falhou:", repr(ie))
            raise

    except Exception as e:
        print("get_or_create_cliente_by_email ERRO:", repr(e))
        raise
    finally:
        try: cur.close()
        except: pass
        conn.close()


# ============================================================================
# Helper: normaliza tipo (mesa enum da tabela cotacoes)
# ============================================================================
TIPOS_VALIDOS = {"Auto", "Residencial", "Vida", "Empresarial"}

def _tipo_db(valor: str) -> str:
    v = (valor or "").strip().title()
    return v if v in TIPOS_VALIDOS else "Auto"


# ============================================================================
# Helper: pega telefone do corretor (se houver)
# ============================================================================
def _telefone_corretor(corretor_id):
    if not corretor_id:
        return None
    conn = get_db_connection()
    cur  = conn.cursor()
    try:
        cur.execute("SELECT telefone FROM usuarios WHERE id=%s LIMIT 1", (corretor_id,))
        row = cur.fetchone()
        return row[0] if row else None
    finally:
        cur.close()
        conn.close()


# ============================================================================
# ROTA: criar cotação (chamada pelo modal do cliente)
# URL usada no front: /api/cliente/cotacoes2
# ============================================================================
@app.route("/api/cliente/cotacoes2", methods=["POST"])
def api_cliente_cotacoes_create():
    """
    Cria uma cotação na tabela 'cotacoes' e devolve JSON:
      { ok: true, id, token, status, corretor_telefone }
    Regras:
      - Usa cliente logado (session) se disponível; senão cria/usa por e-mail.
      - 'corretor_id' pode ser "auto" ou vazio -> grava NULL (distribuição automática).
      - Status inicial sempre 'recebida' (compatível com seu ENUM atual).
    """
    data = request.get_json(silent=True) or {}

    # Campos obrigatórios
    tipo     = _tipo_db(data.get("tipo"))
    nome     = (data.get("nome") or "").strip()
    email    = (data.get("email") or "").strip()
    telefone = (data.get("telefone") or "").strip()
    cep      = (data.get("cep") or "").strip()

    if not all([tipo, nome, email, telefone, cep]):
        return jsonify({"ok": False, "error": "Campos obrigatórios ausentes."}), 400

    extra1 = (data.get("extra1") or "").strip() or None
    extra2 = (data.get("extra2") or "").strip() or None

    # Corretor: "auto" ou vazio => None (NULL)
    cid_raw = data.get("corretor_id")
    if cid_raw in (None, "", "auto"):
        corretor_id = None
    else:
        try:
            corretor_id = int(cid_raw)
        except:
            corretor_id = None

    # Descobre/garante o cliente_id
    try:
        if session.get("user_type") == "Cliente" and session.get("user_id"):
            cliente_id = int(session["user_id"])
        else:
            # Não força login — cria/usa pelo e-mail informado
            cliente_id = get_or_create_cliente_by_email(email=email, nome=nome, telefone=telefone)
    except Exception as e:
        print("Falha ao identificar o cliente:", repr(e))
        return jsonify({"ok": False, "error": "Falha ao identificar o cliente."}), 500

    # Insere a cotação
    conn = get_db_connection()
    cur  = conn.cursor()
    try:
        # 1) Insere com token temporário
        cur.execute("""
            INSERT INTO cotacoes
                (token, cliente_id, corretor_id, tipo, nome, email, telefone, cep, extra1, extra2, status)
            VALUES
                (%s,    %s,         %s,          %s,   %s,    %s,    %s,       %s,  %s,     %s,     %s)
        """, (
            "PENDING", cliente_id, corretor_id, tipo, nome, email, telefone, cep, extra1, extra2, "recebida"
        ))
        novo_id = cur.lastrowid

        # 2) Gera token definitivo baseado no id (estável e legível)
        token = f"SV-{datetime.now().year}-{novo_id:06d}"
        cur.execute("UPDATE cotacoes SET token=%s WHERE id=%s", (token, novo_id))

        conn.commit()

        tel_corretor = _telefone_corretor(corretor_id)

        return jsonify({
            "ok": True,
            "id": novo_id,
            "token": token,
            "status": "recebida",
            "corretor_telefone": tel_corretor
        }), 201

    except Exception as e:
        conn.rollback()
        print("ERRO ao criar cotação:", repr(e))
        return jsonify({"ok": False, "error": "Falha ao salvar a cotação."}), 500
    finally:
        cur.close()
        conn.close()
# ============================================================
# API: listar cotações do cliente logado
# ============================================================
@app.route("/api/cliente/cotacoes/list")
def api_cliente_cotacoes_list():
    if "user_id" not in session or session.get("user_type") != "Segurado":
        return jsonify({"ok": False, "error": "Acesso restrito"}), 403

    user_id = session["user_id"]

    conn = get_db_connection()
    cur  = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT c.id, c.tipo, c.status, c.token, c.criado_em,
                   u.nome AS corretor_nome, u.telefone AS corretor_telefone
            FROM cotacoes c
            LEFT JOIN usuarios u ON u.id = c.corretor_id
            WHERE c.cliente_id = %s
            ORDER BY c.criado_em DESC
            LIMIT 50
        """, (user_id,))
        rows = cur.fetchall() or []
    finally:
        cur.close()
        conn.close()

    # normaliza status (remove acentos e aceita variações)
    def _normalize_status(status: str) -> str:
        if not status:
            return "recebida"
        s = status.strip().lower()
        import unicodedata
        s = "".join(c for c in unicodedata.normalize("NFD", s)
                    if unicodedata.category(c) != "Mn")
        if "analise" in s:
            return "em_analise"
        if "enviad" in s:
            return "enviada"
        return "recebida"

    cotacoes = []
    for r in rows:
        cotacoes.append({
            "id": r["id"],
            "tipo": r.get("tipo") or "—",
            "status": _normalize_status(r.get("status")),
            "token": r.get("token") or f"SV-{datetime.now().year}-{int(r['id']):06d}",
            "criado_em": r.get("criado_em").strftime("%d/%m/%Y %H:%M")
                         if r.get("criado_em") else "—",
            "corretor_nome": r.get("corretor_nome") or "A definir",
            "corretor_telefone": r.get("corretor_telefone")
        })

    return jsonify({"ok": True, "cotacoes": cotacoes})

# Compatibilidade com link .html
@app.route("/minhas_apolices.html")
def minhas_apolices_html():
    return redirect(url_for("cliente_apolices"))

# 🔹 Rota principal - área do cliente / apólices
from datetime import date

@app.route("/cliente/apolices")
def acompanhamento_ap_cliente():
    if "user_id" not in session or session.get("user_type") != "Segurado":
        flash("Acesso restrito! Faça login como cliente.", "danger")
        return redirect(url_for("cliente_login"))

    user_id = session["user_id"]

    try:
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)

        # 🔹 Usuário logado
        cur.execute("SELECT id, nome, cpf, foto_de_perfil FROM usuarios WHERE id = %s", (user_id,))
        user = cur.fetchone() or {"id": user_id, "nome": "Cliente", "cpf": None, "foto_de_perfil": None}

        # 🔹 Busca apólices do cliente
        cur.execute("""
            SELECT
              id, apolice_id, cliente_id, cliente_nome, cpf,
              numero_apolice, numero_proposta, tipo_apolice, seguradora,
              valor_apolice, data_inicio, data_termino, parcelas,
              primeiro_vencimento, forma_pagamento, observacoes, status,
              enviado_em
            FROM apolices_segurado
            WHERE cliente_id = %s
               OR REPLACE(REPLACE(REPLACE(cpf, '.', ''), '-', ''), ' ', '') =
                  REPLACE(REPLACE(REPLACE(%s, '.', ''), '-', ''), ' ', '')
            ORDER BY id DESC
        """, (user["id"], user.get("cpf")))
        apolices = cur.fetchall()

        # 🔹 Formatar campos
        for ap in apolices:
            ap["data_inicio_fmt"] = ap["data_inicio"].strftime("%d/%m/%Y") if ap.get("data_inicio") else "-"
            ap["data_termino_fmt"] = ap["data_termino"].strftime("%d/%m/%Y") if ap.get("data_termino") else "-"
            ap["vencimento_fmt"] = ap["primeiro_vencimento"].strftime("%d/%m/%Y") if ap.get("primeiro_vencimento") else "-"

        # ===== KPIs =====
        total_ativas = sum(1 for ap in apolices if (ap.get("status") or "").lower() == "ativo" or "ativa" in (ap.get("status") or "").lower())
        valor_total = sum(float(ap.get("valor_apolice") or 0) for ap in apolices)

        # Proximos vencimentos (apólices dentro de 30 dias)
        hoje = date.today()
        vencimentos_proximos = sum(
            1 for ap in apolices if ap.get("primeiro_vencimento") and (ap["primeiro_vencimento"] - hoje).days <= 30
        )

        kpis = {
            "ativas": total_ativas,
            "valor_total": valor_total,
            "vencimentos": vencimentos_proximos,
            "cobertura": "100%" if total_ativas else "0%"
        }

        # === Normaliza foto ===
        foto_url = None
        if user and user.get("foto_de_perfil"):
            foto_path = str(user["foto_de_perfil"]).replace("\\", "/")
            if foto_path.startswith("http"):
                foto_url = foto_path
            elif foto_path.startswith("static/"):
                foto_url = url_for("static", filename=foto_path.split("static/", 1)[1])
            else:
                foto_url = url_for("static", filename=foto_path)

    except Exception as e:
        print("Erro ao carregar apólices do cliente:", e)
        user = {"id": user_id, "nome": "Cliente"}
        apolices = []
        kpis = {"ativas": 0, "valor_total": 0, "vencimentos": 0, "cobertura": "0%"}
        foto_url = None

    finally:
        try:
            cur.close()
            conn.close()
        except:
            pass

    # 🔹 Renderizar
    return render_template(
        "acompanhamento_ap_cliente.html",
        user=user,
        foto_url=foto_url,
        apolices=apolices,
        kpis=kpis,
        ACTIVE_MENU="apolices"
    )




# Compatibilidade com link .html (redireciona para o endpoint acima)
@app.route("/minhas_propostas.html")
def minhas_propostas_html():
    return redirect(url_for("minhas_propostas"))

@app.route("/enviar_proposta_segurado", methods=["POST"])
def enviar_proposta_segurado():
    if "user_id" not in session or session.get("user_type") != "Corretor":
        flash("Acesso restrito!", "danger")
        return redirect(url_for("corretor_login"))

    id_proposta = request.form.get("id_proposta")
    cpf_digitado = request.form.get("cpf")

    def normalize_cpf(cpf: str) -> str:
        return (cpf or "").replace(".", "").replace("-", "").strip()

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    # 1) Busca dados da proposta (já incluindo anexos)
    cur.execute("""
        SELECT id, cliente, cpf_cliente, numero_proposta, validade, tipo, seguradora, anotacoes,
               status, valor_total, probabilidade, prazo_estimado,
               documentos_json, fotos_json
          FROM propostas
         WHERE id = %s
    """, (id_proposta,))
    proposta = cur.fetchone()

    if not proposta:
        cur.close(); conn.close()
        flash("Proposta não encontrada.", "danger")
        return redirect(url_for("propostas"))

    # 2) Valida CPF contra tabela usuarios
    cur.execute("SELECT id, nome, cpf FROM usuarios WHERE cpf = %s", (cpf_digitado,))
    segurado = cur.fetchone()
    if not segurado:
        cur.close(); conn.close()
        flash("Nenhum segurado encontrado com este CPF!", "danger")
        return redirect(url_for("propostas"))

    if normalize_cpf(segurado["cpf"]) != normalize_cpf(proposta["cpf_cliente"]):
        cur.close(); conn.close()
        flash("CPF informado não confere com o cliente desta proposta!", "danger")
        return redirect(url_for("propostas"))

    # 3) Inserir/Atualizar propostas_segurado (copiando anexos)
    #    Se já existir um registro para esta proposta_id, fazemos UPDATE; senão, INSERT.
    cur.execute("SELECT id FROM propostas_segurado WHERE proposta_id = %s", (id_proposta,))
    ps_existente = cur.fetchone()

    campos_comuns = (
        segurado["id"],                 # segurado_id
        proposta["cliente"],            # segurado_nome (ou cliente)
        proposta["cpf_cliente"],
        proposta["numero_proposta"],
        proposta["validade"],
        proposta["tipo"],
        proposta["seguradora"],
        proposta["anotacoes"],
        "Enviada",                      # status no espelho
        proposta["valor_total"],
        proposta["probabilidade"],
        proposta["prazo_estimado"],
        proposta.get("documentos_json"),
        proposta.get("fotos_json"),
    )

    if ps_existente:
        # UPDATE
        cur.execute("""
            UPDATE propostas_segurado
               SET segurado_id     = %s,
                   segurado_nome   = %s,
                   cpf_cliente     = %s,
                   numero_proposta = %s,
                   validade        = %s,
                   tipo            = %s,
                   seguradora      = %s,
                   anotacoes       = %s,
                   status          = %s,
                   valor_total     = %s,
                   probabilidade   = %s,
                   prazo_estimado  = %s,
                   documentos_json = %s,
                   fotos_json      = %s,
                   atualizado_em   = NOW()
             WHERE proposta_id     = %s
        """, (*campos_comuns, id_proposta))
    else:
        # INSERT
        cur.execute("""
            INSERT INTO propostas_segurado (
                proposta_id, segurado_id, segurado_nome, cpf_cliente,
                numero_proposta, validade, tipo, seguradora, anotacoes, status,
                valor_total, probabilidade, prazo_estimado,
                documentos_json, fotos_json, criado_em, atualizado_em
            ) VALUES (
                %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s, NOW(), NOW()
            )
        """, (
            proposta["id"], *campos_comuns
        ))

    # 4) Atualiza a proposta original (opcional, mas pedido)
    cur.execute("UPDATE propostas SET status = 'Enviada' WHERE id = %s", (id_proposta,))

    conn.commit()
    cur.close()
    conn.close()

    flash(f"✅ Proposta (com anexos) enviada com sucesso ao segurado {segurado['nome']}.", "success")
    return redirect(url_for("propostas"))


@app.route("/cliente/propostas")
def cliente_propostas_html():
    if "user_id" not in session or session.get("user_type") != "Segurado":
        return redirect(url_for("login"))

    user_id = session["user_id"]

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    # Dados do usuário logado
    cur.execute("SELECT id, nome, cpf, foto_de_perfil FROM usuarios WHERE id = %s", (user_id,))
    user = cur.fetchone()

    # Propostas do segurado
    cur.execute("""
        SELECT *
        FROM propostas_segurado
        WHERE segurado_id = %s
        ORDER BY id DESC
    """, (user["id"],))
    propostas = cur.fetchall()

    cur.close()
    conn.close()

    # 🔹 Gera iniciais (fallback caso não tenha foto)
    iniciais = ""
    if user and user.get("nome"):
        partes = user["nome"].split()
        iniciais = (partes[0][0] + (partes[1][0] if len(partes) > 1 else "")).upper()

    # 🔹 Normaliza a foto para URL acessível
    foto_url = None
    if user and user.get("foto_de_perfil"):
        foto_path = str(user["foto_de_perfil"]).replace("\\", "/")
        if foto_path.startswith("http"):  # se já for URL externa
            foto_url = foto_path
        elif foto_path.startswith("static/"):
            foto_url = url_for("static", filename=foto_path.split("static/", 1)[1])
        else:
            foto_url = url_for("static", filename=foto_path)

    # ===== Estatísticas =====
    total = len(propostas)
    em_analise = 0
    aprovadas = 0
    valor_total = 0.0
    andamento = 0
    aguardando = 0

    for p in propostas:
        status = (p.get("status") or "").lower()
        valor_total += float(p.get("valor_total") or 0)

        if "aprov" in status:
            aprovadas += 1
        elif "analis" in status or "enviad" in status or "aguard" in status:
            em_analise += 1
            if "enviad" in status:
                andamento += 1
            elif "aguard" in status:
                aguardando += 1

    taxa_aprov = f"{round((aprovadas / total) * 100) if total else 0}%"

    kpis = {
        "total": total,
        "analise": em_analise,
        "aprovadas": aprovadas,
        "taxa": taxa_aprov,
        "valor_total": valor_total
    }

    return render_template(
        "acompanhamento_pp_cliente.html",
        user=user,
        foto_url=foto_url,       # 🔹 agora a foto volta a aparecer
        propostas=propostas,
        iniciais=iniciais,
        ACTIVE_MENU="propostas",
        kpis=kpis,
        andamento=andamento,     # 🔹 badges
        aguardando=aguardando    # 🔹 badges
    )

@app.route("/cliente/proposta/pdf", methods=["GET"])
def cliente_proposta_pdf():
    # Somente segurado logado
    if "user_id" not in session or session.get("user_type") != "Segurado":
        from flask import make_response
        return make_response("Acesso restrito. Faça login como segurado.", 403)

    # Imports locais (para não alterar cabeçalho do arquivo)
    import os, json
    from io import BytesIO
    from flask import request, send_file, make_response, current_app
    try:
        from PyPDF2 import PdfMerger
    except Exception:
        PdfMerger = None  # se não tiver, usamos fallback (primeiro PDF)

    # Helper: caminho absoluto a partir de "static/..."
    def _abs_from_static(rel_or_abs: str) -> str:
        if not rel_or_abs:
            return ""
        p = str(rel_or_abs).replace("\\", "/")
        if os.path.isabs(p) and os.path.exists(p):
            return p
        if p.startswith("/"):
            p = p[1:]
        return os.path.join(current_app.root_path, p)

    # Helper: parse documentos_json
    def _parse_docs_json(raw):
        try:
            data = raw if isinstance(raw, list) else json.loads(raw or "[]")
        except Exception:
            data = []
        out = []
        for it in data:
            if isinstance(it, str):
                out.append({"path": it, "original": os.path.basename(it)})
            elif isinstance(it, dict):
                out.append({
                    "path": it.get("path") or it.get("filename") or it.get("url") or "",
                    "original": it.get("original") or it.get("name") or os.path.basename(it.get("path") or it.get("filename") or ""),
                    "mimetype": it.get("mimetype"),
                    "size": it.get("size"),
                })
        return out

    ps_id = request.args.get("ps_id", type=int)
    if not ps_id:
        return make_response("Parâmetro ps_id é obrigatório.", 400)

    # Busca proposta do segurado
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT id, segurado_id, numero_proposta, documentos_json
        FROM propostas_segurado
        WHERE id = %s
    """, (ps_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        return make_response("Proposta do segurado não encontrada.", 404)

    # Autorização: deve pertencer ao usuário logado
    if int(row["segurado_id"]) != int(session.get("user_id")):
        return make_response("Você não tem permissão para este download.", 403)

    # Filtra apenas PDFs
    docs = _parse_docs_json(row.get("documentos_json"))
    pdf_paths = []
    for d in docs:
        abs_path = _abs_from_static(d.get("path"))
        if not abs_path or not os.path.exists(abs_path):
            continue
        if abs_path.lower().endswith(".pdf") or (d.get("mimetype") == "application/pdf"):
            pdf_paths.append(abs_path)

    if not pdf_paths:
        return make_response("Nenhum PDF disponível para esta proposta.", 404)

    # Se houver só um PDF, envia direto
    if len(pdf_paths) == 1 or PdfMerger is None:
        filename = f"proposta_{row.get('numero_proposta') or row['id']}.pdf"
        return send_file(pdf_paths[0], as_attachment=True, download_name=filename, mimetype="application/pdf")

    # Mescla múltiplos PDFs
    merger = PdfMerger()
    try:
        for p in pdf_paths:
            merger.append(p)
        buf = BytesIO()
        merger.write(buf)
        merger.close()
        buf.seek(0)
    except Exception as e:
        try:
            merger.close()
        except Exception:
            pass
        return make_response(f"Erro ao mesclar PDFs: {e}", 500)

    filename = f"proposta_{row.get('numero_proposta') or row['id']}_completa.pdf"
    return send_file(buf, as_attachment=True, download_name=filename, mimetype="application/pdf")


@app.route("/acompanhamento_propostas")
def cliente_propostas():
    # Somente segurados logados
    if "user_id" not in session or session.get("user_type") != "Segurado":
        flash("Acesso restrito! Faça login como cliente.", "danger")
        return redirect(url_for("cliente_login"))

    user_id = session["user_id"]

    try:
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)

        # 🔹 Dados do usuário logado
        cur.execute("SELECT id, nome, cpf, foto_de_perfil FROM usuarios WHERE id = %s", (user_id,))
        user = cur.fetchone() or {"id": user_id, "nome": "Cliente", "cpf": None, "foto_de_perfil": None}

        # 🔹 Propostas do cliente (prioriza ID, mas também compara CPF normalizado)
        cur.execute("""
            SELECT
              id, proposta_id, segurado_id, segurado_nome, cpf_cliente,
              numero_proposta, validade, tipo, seguradora,
              anotacoes, status, valor_total, probabilidade,
              prazo_estimado, criado_em, atualizado_em
            FROM propostas_segurado
            WHERE segurado_id = %s
               OR REPLACE(REPLACE(REPLACE(cpf_cliente, '.', ''), '-', ''), ' ', '') =
                  REPLACE(REPLACE(REPLACE(%s, '.', ''), '-', ''), ' ', '')
            ORDER BY id DESC
        """, (user["id"], user.get("cpf")))
        propostas = cur.fetchall()

    except Exception as e:
        print("Erro ao carregar propostas do cliente:", e)
        user = {"id": user_id, "nome": "Cliente", "foto_url": None}
        propostas = []
    finally:
        try:
            cur.close(); conn.close()
        except Exception:
            pass

    # ===== Helpers =====
    from datetime import datetime, date
    def brl(v):
        try:
            return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except:
            return "R$ 0,00"

    def dmy(x):
        if not x: return "--/--/----"
        if isinstance(x, (date, datetime)):
            return x.strftime("%d/%m/%Y")
        try:
            return datetime.strptime(str(x)[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
        except:
            return str(x)

    def status_info(s):
        s = (s or "").lower()
        if "aprov" in s:   return ("aprovada",  "Aprovada",           100)
        if "reprov" in s:  return ("rejeitada", "Rejeitada",          100)
        if "vencid" in s or "expir" in s:
                           return ("rejeitada", "Expirada",           100)
        if "aguardando seguradora" in s:
                           return ("analise",   "Em Análise",          70)
        if "aguardando cliente" in s or "aguard" in s:
                           return ("aguardando","Aguardando Doc.",     60)
        if "negocia" in s: return ("analise",   "Em Análise",          60)
        if "enviada" in s: return ("analise",   "Em Análise",          40)
        if "nova" in s:    return ("pendente",  "Pendente",            10)
        return ("pendente","Pendente",           20)

    # Enriquecimento para o template
    total = len(propostas)
    em_analise = aprovadas = 0
    for p in propostas:
        cls, label, pct = status_info(p.get("status"))
        p["_status_cls"]   = cls
        p["_status_label"] = label
        p["_pct"]          = pct
        p["_data"]         = dmy(p.get("validade") or p.get("criado_em"))
        p["_valor"]        = brl(p.get("valor_total") or 0)
        p["_tipo_key"]     = (p.get("tipo") or "").strip().lower()

        if cls in ("analise","aguardando"):
            em_analise += 1
        if cls == "aprovada":
            aprovadas += 1

    taxa_aprov = f"{round((aprovadas/total)*100) if total else 0}%"

    # 🔹 Gera iniciais do cliente
    iniciais = ""
    if user and user.get("nome"):
        partes = user["nome"].split()
        if len(partes) >= 2:
            iniciais = partes[0][0].upper() + partes[1][0].upper()
        else:
            iniciais = partes[0][0].upper()

            print("DEBUG propostas:", propostas)

    return render_template(
        "acompanhamento_pp_cliente.html",
        user=user,
        foto_url=user.get("foto_de_perfil"),
        propostas=propostas,
        iniciais=iniciais,
        kpis={
            "total": total,
            "analise": em_analise,
            "aprovadas": aprovadas,
            "taxa": taxa_aprov
        }
    )

def formatar_cpf(cpf: str) -> str:
    """Formata CPF para o padrão 000.000.000-00"""
    if not cpf:
        return ""
    cpf = ''.join(filter(str.isdigit, str(cpf)))  # mantém só números
    if len(cpf) == 11:
        return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"
    return cpf  # retorna como veio se não for válido


ALLOWED_DOCS = {'.pdf','.doc','.docx','.xls','.xlsx','.csv','.txt','.ppt','.pptx','.zip','.rar','.7z','.odt','.ods'}
ALLOWED_IMGS = {'.jpg','.jpeg','.png','.webp','.gif'}

# Base pública para uploads do "espelho" do segurado
UPLOAD_SEG_BASE = os.path.join('static', 'uploads', 'sinistros_segurado')

def _ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

def _ext_ok(filename: str, allowed: set) -> bool:
    ext = os.path.splitext(filename or "")[1].lower()
    return ext in allowed

def _unique_name(original: str) -> str:
    base, ext = os.path.splitext(secure_filename(original or "file"))
    return f"{base}__{uuid.uuid4().hex[:8]}{ext}"


@app.route("/enviar_sinistro_segurado", methods=["POST"])
def enviar_sinistro_segurado():
    if "user_id" not in session or session.get("user_type") != "Corretor":
        flash("Acesso restrito!", "danger")
        return redirect(url_for("corretor_login"))

    id_sinistro = request.form.get("id_sinistro")
    cpf_digitado = request.form.get("cpf_confirmacao")

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    # 1) Busca sinistro já trazendo anexos existentes
    cur.execute("""
        SELECT 
            s.id               AS sinistro_id,
            s.cliente,
            s.cpf_cliente,
            s.numero_apolice,
            s.tipo,
            s.data_ocorrencia,
            s.`local`,
            s.descricao,
            s.valor_estimado,
            s.status,
            s.seguradora,
            s.documentos_json,
            s.fotos_json
        FROM sinistros s
        WHERE s.id = %s
    """, (id_sinistro,))
    sinistro = cur.fetchone()

    if not sinistro:
        flash("Sinistro não encontrado.", "danger")
        return redirect(url_for("sinistros"))

    # 2) Valida CPF contra tabela usuarios
    cur.execute("SELECT id, nome, email, telefone, cpf FROM usuarios WHERE cpf = %s", (cpf_digitado,))
    segurado = cur.fetchone()

    if not segurado:
        flash("Nenhum segurado encontrado com este CPF!", "danger")
        return redirect(url_for("sinistros"))

    def _norm_cpf(cpf: str) -> str:
        return (cpf or "").replace(".", "").replace("-", "").strip()

    if _norm_cpf(segurado["cpf"]) != _norm_cpf(sinistro["cpf_cliente"]):
        flash("CPF informado não confere com o cliente deste sinistro!", "danger")
        return redirect(url_for("sinistros"))

    # 3) Converte anexos existentes do sinistro (se houver)
    try:
        docs_exist = json.loads(sinistro.get("documentos_json") or "[]")
        if not isinstance(docs_exist, list): docs_exist = []
    except Exception:
        docs_exist = []

    try:
        fotos_exist = json.loads(sinistro.get("fotos_json") or "[]")
        if not isinstance(fotos_exist, list): fotos_exist = []
    except Exception:
        fotos_exist = []

    # 4) Processa novos uploads vindos do formulário do modal
    #    (name="documentos[]" e name="fotos[]")
    base_dir = os.path.join(UPLOAD_SEG_BASE, str(sinistro["sinistro_id"]))
    docs_dir = os.path.join(base_dir, "documentos")
    fotos_dir = os.path.join(base_dir, "fotos")
    _ensure_dir(docs_dir); _ensure_dir(fotos_dir)

    novos_docs = []
    for f in request.files.getlist("documentos[]"):
        if not f or not f.filename or not _ext_ok(f.filename, ALLOWED_DOCS):
            continue
        fname = _unique_name(f.filename)
        f.save(os.path.join(docs_dir, fname))
        novos_docs.append(os.path.join('static', 'uploads', 'sinistros_segurado',
                                       str(sinistro["sinistro_id"]), 'documentos', fname).replace("\\","/"))

    novas_fotos = []
    for f in request.files.getlist("fotos[]"):
        if not f or not f.filename or not _ext_ok(f.filename, ALLOWED_IMGS):
            continue
        fname = _unique_name(f.filename)
        f.save(os.path.join(fotos_dir, fname))
        novas_fotos.append(os.path.join('static', 'uploads', 'sinistros_segurado',
                                        str(sinistro["sinistro_id"]), 'fotos', fname).replace("\\","/"))

    # 5) Mescla: anexos existentes do sinistro + novos enviados no modal
    docs_final  = (docs_exist or []) + (novos_docs or [])
    fotos_final = (fotos_exist or []) + (novas_fotos or [])

    # 6) Insere espelho na sinistros_segurado (incluindo JSONs de anexos)
    cur.execute("""
        INSERT INTO sinistros_segurado (
            sinistro_id, cliente_id, apolice_id, cliente_nome, cpf, email, telefone,
            numero_apolice, tipo_apolice, seguradora, data_ocorrencia, tipo_sinistro,
            local_ocorrencia, descricao, valor_estimado, status, enviado_em,
            documentos_json, fotos_json
        ) VALUES (
            %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW(),
            %s,%s
        )
    """, (
        sinistro["sinistro_id"], segurado["id"], 0,
        segurado["nome"], segurado["cpf"], segurado["email"], segurado["telefone"],
        sinistro["numero_apolice"], sinistro["tipo"], sinistro["seguradora"],
        sinistro["data_ocorrencia"], sinistro["tipo"], sinistro["local"],
        sinistro["descricao"], sinistro["valor_estimado"], "Enviado",
        json.dumps(docs_final, ensure_ascii=False) if docs_final else None,
        json.dumps(fotos_final, ensure_ascii=False) if fotos_final else None
    ))

    # 7) Atualiza status do sinistro original
    cur.execute("UPDATE sinistros SET status=%s WHERE id=%s",
                ("Enviado ao segurado", id_sinistro))

    conn.commit()
    cur.close(); conn.close()

    flash(f"✅ Sinistro enviado com sucesso ao segurado {segurado['nome']}.", "success")
    return redirect(url_for("sinistros", sucesso="true"))

@app.route("/cliente/sinistro/anexos-pdf", methods=["GET"])
def cliente_sinistro_anexos_pdf():
    # ---- quem é o usuário logado? (tolera diferentes chaves na sessão)
    def current_user_id():
        for k in ("user_id", "cliente_id"):
            if session.get(k): return int(session[k])
        u = session.get("user") or {}
        if isinstance(u, dict) and u.get("id"): return int(u["id"])
        return None

    uid = current_user_id()
    if not uid or session.get("user_type") != "Segurado":
        return ("Acesso restrito. Faça login como segurado.", 403)

    from flask import request, send_file, current_app, make_response
    import os, json
    from io import BytesIO
    try:
        from PyPDF2 import PdfMerger
    except Exception:
        PdfMerger = None

    # ---- parâmetro único (ref pode ser sinistro_id ou id)
    ref = request.args.get("ref", type=int)
    if not ref:
        # compat: se vier sinistro_id explicitamente
        ref = request.args.get("sinistro_id", type=int)
    if not ref:
        return ("Parâmetro ref/sinistro_id é obrigatório.", 400)

    # ---- tenta achar por sinistro_id; se não achar, tenta por id
    conn = get_db_connection(); cur = conn.cursor(dictionary=True)

    cur.execute("""
        SELECT id, sinistro_id, cliente_id, numero_apolice, seguradora, documentos_json
        FROM sinistros_segurado
        WHERE sinistro_id = %s
        LIMIT 1
    """, (ref,))
    row = cur.fetchone()

    if not row:
        cur.execute("""
            SELECT id, sinistro_id, cliente_id, numero_apolice, seguradora, documentos_json
            FROM sinistros_segurado
            WHERE id = %s
            LIMIT 1
        """, (ref,))
        row = cur.fetchone()

    cur.close(); conn.close()

    if not row:
        return ("Sinistro não encontrado.", 404)

    if int(row["cliente_id"]) != int(uid):
        return ("Você não tem permissão para este download.", 403)

    # ---- normaliza caminhos e filtra PDFs do documentos_json
    def abs_from_static(p):
        if not p: return ""
        p = str(p).replace("\\","/")
        if os.path.isabs(p) and os.path.exists(p): return p
        if p.startswith("/"): p = p[1:]
        base = current_app.root_path
        if p.startswith("static/"): return os.path.join(base, p)
        return os.path.join(base, "static", p)

    def parse_docs(raw):
        try:
            data = raw if isinstance(raw, list) else json.loads(raw or "[]")
        except Exception:
            data = []
        out = []
        for it in data:
            if isinstance(it, str):
                out.append({"path": it, "mimetype": None})
            elif isinstance(it, dict):
                out.append({"path": it.get("path") or it.get("filename") or it.get("url"),
                            "mimetype": it.get("mimetype") or it.get("content_type")})
        return out

    docs = parse_docs(row.get("documentos_json"))
    pdfs = []
    for d in docs:
        ap = abs_from_static(d.get("path"))
        if ap and os.path.exists(ap) and (ap.lower().endswith(".pdf") or d.get("mimetype") == "application/pdf"):
            pdfs.append(ap)

    if not pdfs:
        return ("Nenhum PDF disponível para este sinistro.", 404)

    # ---- envia único PDF ou mescla
    if len(pdfs) == 1 or PdfMerger is None:
        return send_file(pdfs[0], as_attachment=True,
                         download_name=f"sinistro_{row.get('sinistro_id') or row['id']}.pdf",
                         mimetype="application/pdf")

    merger = PdfMerger()
    buf = BytesIO()
    for p in pdfs: merger.append(p)
    merger.write(buf); merger.close(); buf.seek(0)
    return send_file(buf, as_attachment=True,
                     download_name=f"sinistro_{row.get('sinistro_id') or row['id']}_anexos.pdf",
                     mimetype="application/pdf")

@app.route("/cliente/sinistros")
def sinistros_segurado():
    if "user_id" not in session or session.get("user_type") != "Segurado":
        return redirect(url_for("cliente_login"))

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    try:
        # Busca sinistros do cliente logado
        cur.execute("""
            SELECT 
                s.id AS sinistro_id,
                s.numero_apolice,
                s.tipo_sinistro,
                s.data_ocorrencia,
                s.valor_estimado,
                s.status,
                s.descricao,
                s.local_ocorrencia,
                    s.seguradora
            FROM sinistros_segurado s
            WHERE s.cliente_id = %s
            ORDER BY s.data_ocorrencia DESC
        """, (session["user_id"],))
        sinistros = cur.fetchall()

        # Dados do cliente (foto + nome)
        cur.execute("""
            SELECT nome, foto_de_perfil
            FROM usuarios
            WHERE id = %s
        """, (session["user_id"],))
        user = cur.fetchone()

    finally:
        cur.close()
        conn.close()

    # Normaliza imagem de perfil
    foto_url = None
    if user and user.get("foto_de_perfil"):
        path = str(user["foto_de_perfil"]).replace("\\", "/")
        if path.startswith("http"):
            foto_url = path
        elif path.startswith("static/"):
            foto_url = url_for("static", filename=path.split("static/", 1)[1])
        else:
            foto_url = url_for("static", filename=path)

    # ===== KPIs (indicadores) =====
    total_sinistros = len(sinistros)

    # Status considerados "em andamento"
    andamento_status = ["enviado", "em análise", "em analise", "aguardando", "pendente"]
    em_analise = sum(
        1 for s in sinistros if s["status"] and s["status"].strip().lower() in andamento_status
    )

    # Status considerados "concluídos"
    concluido_status = ["concluído", "concluido", "aprovado", "finalizado"]
    concluidos = sum(
        1 for s in sinistros if s["status"] and s["status"].strip().lower() in concluido_status
    )

    # Valor total indenizado (só soma concluídos/aprovados)
    valor_indenizado = sum(
        (s["valor_estimado"] or 0)
        for s in sinistros
        if s["status"] and s["status"].strip().lower() in concluido_status
    )

    kpis = {
        "total": total_sinistros,
        "em_analise": em_analise,
        "concluidos": concluidos,
        "valor_indenizado": valor_indenizado,
    }

    return render_template(
        "acompanhamento_sn_cliente.html",
        sinistros=sinistros,
        user=user,
        foto_url=foto_url,
        kpis=kpis,
        ACTIVE_MENU="sinistros"
    )

# ------------ Helpers ------------
def only_digits(s: str) -> str:
    return re.sub(r'\D', '', s or '')

def validate_cpf(cpf: str) -> bool:
    cpf = only_digits(cpf)
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
    d1 = (soma * 10) % 11
    d1 = 0 if d1 == 10 else d1
    if d1 != int(cpf[9]): return False
    soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
    d2 = (soma * 10) % 11
    d2 = 0 if d2 == 10 else d2
    return d2 == int(cpf[10])

def validate_cnpj(cnpj: str) -> bool:
    cnpj = only_digits(cnpj)
    if len(cnpj) != 14 or cnpj == cnpj[0] * 14:
        return False
    pesos1 = [5,4,3,2,9,8,7,6,5,4,3,2]
    d1 = 11 - (sum(int(cnpj[i]) * pesos1[i] for i in range(12)) % 11)
    d1 = 0 if d1 >= 10 else d1
    if d1 != int(cnpj[12]): return False
    pesos2 = [6] + pesos1
    d2 = 11 - (sum(int(cnpj[i]) * pesos2[i] for i in range(13)) % 11)
    d2 = 0 if d2 >= 10 else d2
    return d2 == int(cnpj[13])

@app.route("/corretor_cadastro.html", methods=["GET", "POST"])
def corretor_cadastro():
    if request.method == "POST":
        nome = (request.form.get("nome") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        telefone = only_digits(request.form.get("telefone") or "")
        cpf = only_digits(request.form.get("cpf") or "")
        cnpj = only_digits(request.form.get("cnpj") or "")
        genero = (request.form.get("genero") or "").strip() or None
        tipo = (request.form.get("tipo") or "Corretor").strip()
        senha = request.form.get("senha")

        if tipo not in ("Corretor", "Administrador"):
            tipo = "Corretor"

        if not nome or not email or not senha:
            flash("Preencha nome, e-mail e senha.", "danger")
            return redirect(request.url)

        # Exatamente um entre CPF/CNPJ
        if (bool(cpf) + bool(cnpj)) != 1:
            flash("Preencha somente CPF ou somente CNPJ (um dos dois).", "danger")
            return redirect(request.url)

        if cpf and not validate_cpf(cpf):
            flash("CPF inválido.", "danger")
            return redirect(request.url)
        if cnpj and not validate_cnpj(cnpj):
            flash("CNPJ inválido.", "danger")
            return redirect(request.url)

        senha_hash = generate_password_hash(senha)

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO usuarios
                    (nome, email, senha_hash, tipo, telefone, genero, cpf, cnpj)
                VALUES
                    (%s,   %s,    %s,         %s,   %s,       %s,     %s,  %s)
                """,
                (nome, email, senha_hash, tipo, telefone or None, genero, cpf or None, cnpj or None)
            )
            conn.commit()
            flash("Cadastro realizado com sucesso!", "success")
            return redirect(url_for("corretor_login"))
        except Error as err:
            print("ERRO MYSQL:", err)  # aparece no console do Flask
            errno = getattr(err, "errno", None)
            msg = str(err)
            if errno == 1062:
                # Duplicidade
                low = msg.lower()
                if "email" in low:
                    flash("Este e-mail já está cadastrado.", "danger")
                elif "cpf" in low:
                    flash("Este CPF já está cadastrado.", "danger")
                elif "cnpj" in low:
                    flash("Este CNPJ já está cadastrado.", "danger")
                else:
                    flash("Registro duplicado.", "danger")
            elif "Unknown column" in msg or "Column not found" in msg:
                flash("Colunas (telefone/genero/cpf/cnpj) não existem. Rode os ALTER TABLE no MySQL.", "danger")
            else:
                flash(f"Erro ao cadastrar: {msg}", "danger")
        finally:
            cursor.close()
            conn.close()

    return render_template("corretor_cadastro.html")

def date_br(dt):
    """Formata datas para DD/MM/YYYY"""
    if not dt:
        return ""
    if isinstance(dt, str):
        try:
            dt = datetime.strptime(dt[:10], "%Y-%m-%d")
        except Exception:
            try:
                dt = datetime.fromisoformat(dt)
            except Exception:
                return dt
    return dt.strftime("%d/%m/%Y")

def brl(value):
    """Formata valores em moeda BRL"""
    try:
        v = float(value or 0)
        s = f"R$ {v:,.2f}"
        return s.replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "R$ 0,00"

# 🔹 registra no Jinja
app.jinja_env.filters["datebr"] = date_br
app.jinja_env.filters["brl"] = brl


import os
from flask import request, jsonify, current_app
from werkzeug.utils import secure_filename

import os
from flask import request, jsonify, current_app
from werkzeug.utils import secure_filename

import os
from flask import request, jsonify, current_app
from werkzeug.utils import secure_filename

@app.route("/upload_arquivo_apolice/<int:apolice_id>", methods=["POST"])
def upload_arquivo_apolice(apolice_id):
    """Faz upload e vincula o arquivo à apólice (coluna arquivo_anexo)"""
    file = request.files.get("arquivo")
    if not file:
        return jsonify({"success": False, "error": "Nenhum arquivo recebido"}), 400

    # 🔹 Diretório de destino
    pasta_destino = os.path.join(current_app.root_path, "static", "uploads", "apolices")
    os.makedirs(pasta_destino, exist_ok=True)

    # 🔹 Nome seguro e caminho físico
    nome_arquivo = secure_filename(file.filename)
    nome_final = f"{apolice_id}_{nome_arquivo}"
    caminho_final = os.path.join(pasta_destino, nome_final)
    file.save(caminho_final)

    # 🔹 Caminho relativo salvo no banco
    caminho_relativo = f"static/uploads/apolices/{nome_final}"

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Atualiza o caminho do arquivo na apólice
        cur.execute("""
            UPDATE apolices_segurado
            SET arquivo_anexo = %s,
                updated_at = NOW()
            WHERE apolice_id = %s
        """, (caminho_relativo, apolice_id))
        conn.commit()

        if cur.rowcount == 0:
            cur.close()
            conn.close()
            return jsonify({"success": False, "error": "Apólice não encontrada"}), 404

        cur.close()
        conn.close()

        # 🔹 Retorna dados para o JS atualizar o HTML automaticamente
        return jsonify({
            "success": True,
            "message": "Arquivo salvo com sucesso!",
            "arquivo": {
                "nome": nome_arquivo,
                "caminho": caminho_relativo
            }
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/excluir_anexo/<int:apolice_id>', methods=['DELETE'])
def excluir_anexo(apolice_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Verifica se o campo realmente existe e se há registro
        cursor.execute("""
            SELECT arquivo_anexo 
            FROM apolices_segurado 
            WHERE id = %s OR apolice_id = %s
        """, (apolice_id, apolice_id))
        registro = cursor.fetchone()

        if not registro:
            return jsonify(success=False, error="Apólice não encontrada."), 404

        arquivo = registro.get("arquivo_anexo")

        if not arquivo:
            return jsonify(success=False, error="Nenhum arquivo encontrado."), 404

        import os
        caminho_completo = os.path.join(app.root_path, arquivo)
        if os.path.exists(caminho_completo):
            os.remove(caminho_completo)

        # Atualiza o campo no banco
        cursor.execute("""
            UPDATE apolices_segurado 
            SET arquivo_anexo = NULL 
            WHERE id = %s OR apolice_id = %s
        """, (apolice_id, apolice_id))
        conn.commit()

        cursor.close()
        conn.close()

        return jsonify(success=True, message="Arquivo excluído com sucesso!", html='<span class="anexo-vazio">Nenhum arquivo</span>')

    except Exception as e:
        print("Erro ao excluir anexo:", e)
        return jsonify(success=False, error=str(e)), 500
    
from flask import send_file, jsonify
import os

@app.route('/download_apolice/<int:apolice_id>')
def download_apolice(apolice_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT arquivo_anexo 
            FROM apolices_segurado 
            WHERE id = %s OR apolice_id = %s
        """, (apolice_id, apolice_id))
        ap = cursor.fetchone()
        cursor.close()
        conn.close()

        if not ap or not ap['arquivo_anexo']:
            # Retorna JSON para o fetch() entender
            return jsonify(success=False, message="Nenhum arquivo disponível para esta apólice."), 404

        caminho_relativo = ap['arquivo_anexo']
        caminho_absoluto = os.path.join(app.root_path, caminho_relativo)

        if not os.path.exists(caminho_absoluto):
            return jsonify(success=False, message="O arquivo não foi encontrado no servidor."), 404

        return send_file(
            caminho_absoluto,
            as_attachment=True,
            download_name=os.path.basename(caminho_absoluto)
        )

    except Exception as e:
        print("Erro no download_apolice:", e)
        return jsonify(success=False, message=str(e)), 500
    
from flask import jsonify, session, current_app
import os

def _abs_static(path_like: str) -> str | None:
    """
    Converte o valor salvo no BD (ex.: 'static/uploads/x.png' ou 'uploads/x.png')
    para caminho absoluto dentro do seu /static. Retorna None se não parecer local.
    """
    if not path_like:
        return None
    p = str(path_like).strip()
    if p.startswith(("http://", "https://")):
        return None  # era uma URL externa, não apagamos
    # normaliza
    if p.startswith("static/"):
        p = p[len("static/"):]
    return os.path.join(app.root_path, "static", p)

@app.route("/api/corretor/remover-foto", methods=["POST"], endpoint="remover_foto_corretor")
def remover_foto_corretor():
    try:
        # 1) Autenticação
        uid = session.get("user_id")
        utype = session.get("user_type")
        if not uid:
            return jsonify(success=False, message="Não autenticado."), 401
        # se quiser travar só para corretores, mantenha a linha abaixo:
        if utype not in ("Corretor", "corretor"):
            return jsonify(success=False, message="Apenas corretores podem remover a foto."), 403

        # 2) Buscar valor atual para tentar apagar o arquivo
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)

        cur.execute("SELECT foto_de_perfil FROM usuarios WHERE id = %s LIMIT 1", (uid,))
        row = cur.fetchone()
        if not row:
            cur.close(); conn.close()
            return jsonify(success=False, message="Usuário não encontrado."), 404

        foto_atual = row.get("foto_de_perfil") or ""

        # 3) Zerar coluna
        cur.execute("UPDATE usuarios SET foto_de_perfil = NULL WHERE id = %s", (uid,))
        conn.commit()
        cur.close(); conn.close()

        # 4) Apagar arquivo físico (se local)
        try:
            abs_path = _abs_static(foto_atual)
            if abs_path and os.path.isfile(abs_path):
                os.remove(abs_path)
        except Exception as e:
            app.logger.warning("Falha ao apagar arquivo da foto (%s): %s", foto_atual, e)

        return jsonify(success=True, message="Foto removida com sucesso.")
    except Exception as e:
        app.logger.exception("Erro em remover_foto_corretor: %s", e)
        return jsonify(success=False, message=f"Erro no servidor: {e}"), 500
    

from flask import request, jsonify
import hashlib, math
import datetime as dt  

@app.route("/cotacoes/json", methods=["POST"])
def cotacoes_json():
    payload = request.get_json(silent=True) or {}
    tipo = (payload.get("tipo_seguro") or "").strip().lower()
    dados = payload.get("dados") or {}

    if tipo not in {"automovel", "residencial", "vida", "empresarial"}:
        return jsonify({"ok": False, "erro": "tipo_seguro inválido"}), 400

    def seed_num(texto: str) -> float:
        h = hashlib.sha256((texto or "").encode("utf-8")).hexdigest()
        return 0.8 + (int(h[:6], 16) / 0xFFFFFF) * 0.4

    base_por_tipo = {
        "automovel": 180.0, "residencial": 65.0, "vida": 45.0, "empresarial": 220.0,
    }

    risco = seed_num(str(dados))
    risco *= 1.00 + (0.08 if str(dados.get("cidade","")).strip() == "" else 0.0)
    risco *= 1.00 + (0.10 if str(dados.get("cep_pernoite","")).strip() == "" else 0.0)
    if tipo == "automovel":
        ano_modelo = int((str(dados.get("ano_modelo") or "0").strip()[:4] or 0))
        if ano_modelo:
            risco *= 0.98 if ano_modelo >= 2021 else 1.05

    base = base_por_tipo[tipo] * risco

    seguradoras = [
        {"sigla": "PTO", "nome": "Porto"},
        {"sigla": "BRD", "nome": "Bradesco Seguros"},
        {"sigla": "TKM", "nome": "Tokio Marine"},
        {"sigla": "ALL", "nome": "Allianz"},
    ]

    COB = {
        "automovel": [
            ["Colisão", "Roubo/Furto", "Incêndio", "RCF Terceiros R$100 mil"],
            ["Colisão", "Roubo/Furto", "RCF Terceiros R$200 mil", "Vidros"],
            ["Roubo/Furto", "Perda Total", "RCF Terceiros R$50 mil", "Guincho"],
            ["Colisão", "Roubo/Furto", "Perda Total", "Carro Reserva 7 dias"],
        ],
        "residencial": [
            ["Incêndio", "Danos Elétricos", "Roubo", "Vendaval"],
            ["Incêndio", "Roubo", "Quebra de Vidros", "Responsabilidade Civil"],
            ["Incêndio", "Alagamento", "Vendaval", "RC Familiar"],
            ["Incêndio", "Roubo", "Impacto de Veículos", "Danos Elétricos"],
        ],
        "vida": [
            ["Morte", "IPA", "Invalidez por Acidente"],
            ["Morte", "IPD", "Doenças Graves"],
            ["Morte", "IPA", "Assistência Funeral"],
            ["Morte", "IPA", "Diária por Incapacidade Temporária"],
        ],
        "empresarial": [
            ["Incêndio", "Roubo", "RC Operações", "Lucros Cessantes"],
            ["Incêndio", "Danos Elétricos", "Roubo", "Alagamento"],
            ["Incêndio", "RC Produtos", "Roubo", "Quebra de Vidros"],
            ["Incêndio", "RC Geral", "Vendaval", "Roubo de Valores"],
        ],
    }
    AST = {
        "automovel": [
            ["Guincho 200km", "Chaveiro", "Troca de Pneu"],
            ["Guincho 400km", "Carro Reserva 7d", "Pane Seca"],
            ["Guincho 100km", "Translado", "Chaveiro"],
            ["Guincho Ilimitado", "Carro Reserva 15d", "Hospedagem"],
        ],
        "residencial": [
            ["Chaveiro", "Encanador", "Eletricista"],
            ["Guarda-móveis", "Chaveiro", "Limpeza pós-sinistro"],
            ["Eletricista", "Vidraceiro", "Telhadista"],
            ["Chaveiro", "Encanador", "Assistência 24h"],
        ],
        "vida": [
            ["Telemedicina 24h", "Descontos Farmácia"],
            ["Assistência Funeral", "Orientação Nutricional"],
            ["Check-up Anual", "Telemedicina 24h"],
            ["Benefícios Clube", "Assistência Funeral"],
        ],
        "empresarial": [
            ["Assistência Elétrica", "Hidráulica 24h"],
            ["Vigilância", "Limpeza Pós-sinistro"],
            ["Engenheiro Emergencial", "Chaveiro"],
            ["Assistência Técnica", "Gerador Emergencial"],
        ],
    }

    hoje = dt.date.today()                             # <<< aqui estava quebrando
    validade = (hoje + dt.timedelta(days=7)).isoformat()

    propostas = []
    for i, seg in enumerate(seguradoras):
        fator = 1.0 + (i * 0.06) - 0.05
        premio_mensal = round(base * fator, 2)

        if tipo == "automovel":
            try:
                fipe = float(str(dados.get("valor_fipe","0")
                                 ).replace("R$","").replace(".","").replace(",",".").strip() or 0)
            except Exception:
                fipe = 0.0
            franquia = int((fipe * 0.04) or 2500) + i * 300
        else:
            franquia = 0

        score = round(7.8 + (i * 0.4) + (seed_num(seg["sigla"]) - 1.0), 1)
        propostas.append({
            "id": f"{seg['sigla']}-{hashlib.md5((seg['sigla']+tipo).encode()).hexdigest()[:6]}",
            "seguradora": seg["nome"],
            "premio_mensal": float(f"{premio_mensal:.2f}"),
            "franquia": franquia,
            "coberturas": COB[tipo][i],
            "assistencias": AST[tipo][i],
            "score": score,
            "moeda": "BRL",
            "validade": validade,
            "prazo_pagamento": "Mensal",
            "tipo_seguro": tipo,
        })

    return jsonify({"ok": True, "tipo_seguro": tipo, "propostas": propostas, "count": len(propostas)}), 200

import re

def parse_year(v, default=0):
    """
    Extrai um ano (4 dígitos) de uma string como 'Selecione', '2022', '2022/2021', etc.
    Se não achar, retorna default.
    """
    s = str(v or "").strip()
    m = re.search(r"\b(19|20)\d{2}\b", s)
    if m:
        try:
            return int(m.group(0))
        except Exception:
            return default
    try:
        return int(s)  # caso venha "2023"
    except Exception:
        return default

def parse_brl(v, default=0.0):
    """
    Converte 'R$ 45.000,90' -> 45000.90. Se inválido, default.
    """
    s = str(v or "").strip()
    s = s.replace("R$", "").replace(".", "").replace(" ", "").replace(",", ".")
    try:
        return float(s)
    except Exception:
        return default



# 🔹 Servir arquivos estáticos (CSS, JS, imagens)
@app.route("/css/<path:filename>")
def serve_css(filename):
    return send_from_directory("css", filename)

@app.route("/js/<path:filename>")
def serve_js(filename):
    return send_from_directory("js", filename)

@app.route("/imagens/<path:filename>")
def serve_images(filename):
    return send_from_directory("imagens", filename)

# 🔹 Inicia o servidor Flask
if __name__ == "__main__":
    app.run(debug=True)




    