"""
Script para gerar hashes de senhas para config_auth.yaml
Uso: python generate_password.py
"""
import streamlit_authenticator as stauth

print("=" * 60)
print("Gerador de Hash de Senhas - IDT Analyzer")
print("=" * 60)
print()

# Senhas padrão para os usuários
passwords = {
    "admin": "admin123",
    "pm1": "pm123",
    "consultor1": "cons123"
}

print("Gerando hashes para as senhas padrão:\n")

# Usar a API correta do streamlit-authenticator
hasher = stauth.Hasher()
for username, password in passwords.items():
    hashed = hasher.hash(password)
    print(f"{username}:")
    print(f"  Senha: {password}")
    print(f"  Hash:  {hashed}")
    print()

print("=" * 60)
print("Copie os hashes acima para o arquivo config_auth.yaml")
print("⚠️  Altere as senhas em produção!")
print("=" * 60)
