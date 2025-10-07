import socket
import json
import os

BROADCAST_PORT = 37020

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("", BROADCAST_PORT))

print("Aguardando anúncio do servidor...")

data, addr = sock.recvfrom(1024)
msg = data.decode()
name, ip, port = msg.split(";")

print(f"Servidor encontrado: {name} em {ip}:{port}")



HOST = ip  # coloque aqui o IP da máquina do servidor
PORT = int(port)  # Porta TCP do servidor



query = ""

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect((HOST, PORT))

def requestBD(pedido):
    result = {'ok': False, 'payload': None, 'raw': None, 'error': None}
    try:
        try:
            client.sendall(pedido.encode())
            data = client.recv(8192).decode()
        except Exception:
            try:
                client.close()
            except Exception:
                pass
            client2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client2.connect((HOST, PORT))
            client2.sendall(pedido.encode())
            data = client2.recv(8192).decode()
            try:
                client2.close()
            except Exception:
                pass

        result['raw'] = data
        print("Resposta do servidor:", data)
        if not data:
            result['ok'] = True
            result['payload'] = None
            return result
        try:
            parsed = json.loads(data)
            result['ok'] = True
            result['payload'] = parsed
            return result
        except Exception:
            result['ok'] = True
            result['payload'] = data.strip()
            return result
    except Exception as e:
        result['error'] = str(e)
        return result
    

def enviar_imagem(caminho_imagem):
    nome_arquivo = os.path.basename(caminho_imagem)
    tamanho = os.path.getsize(caminho_imagem)

    with open(caminho_imagem, "rb") as f:
        dados = f.read()

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((HOST, PORT))

    sock.sendall((nome_arquivo + "\n").encode())
    sock.sendall((str(tamanho) + "\n").encode())
    sock.sendall(dados)

    resposta = sock.recv(1024).decode()
    print("Resposta do servidor:", resposta)
    sock.close()

if __name__ == "__main__":
    enviar_imagem("imagens_salvas/desenho.png")




