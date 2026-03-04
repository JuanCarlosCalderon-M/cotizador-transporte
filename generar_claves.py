import streamlit_authenticator as stauth

# 1. Escribe aquí las contraseñas reales que quieres asignarle a tus usuarios
contrasenas_reales = ['Esgari2025!', 'Chavita123']

# 2. La librería las encriptará usando el método actualizado
contrasenas_encriptadas = [stauth.Hasher.hash(password) for password in contrasenas_reales]

# 3. Te las mostramos en la pantalla para que las copies
for real, encriptada in zip(contrasenas_reales, contrasenas_encriptadas):
    print(f"Contraseña original: {real}")
    print(f"Hash para pegar en yaml: '{encriptada}'")
    print("-" * 50)