# app.py
#
# Ponto de entrada da aplicação. create_app() (padrão factory) monta a app
# Flask e o servidor Socket.IO; aqui apenas os instanciamos e, em execução
# direta, subimos o servidor de desenvolvimento.
#
# Obs.: em Docker/produção quem sobe a app é o comando do compose
# (flask run / gunicorn), então o bloco __main__ roda só localmente.

from myapp import create_app

# socketIo é devolvido junto porque o run precisa dele (não basta app.run).
app, socketIo = create_app()

if __name__ == "__main__":
    # debug=True: autoreload + traceback. Não usar assim em produção.
    socketIo.run(app, debug=True)