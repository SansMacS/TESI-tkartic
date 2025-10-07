import socket
import sqlite3
import json
import threading
import time

HOST = '192.168.0.101'   # IP do servidor
PORT = 5000             # Porta TCP do servidor
BROADCAST_IP = "192.168.0.255"  # endereço de broadcast da rede
BROADCAST_PORT = 37020          # porta UDP para broadcast

def handle_client(conn, addr):
    print(f"Conexão de {addr}")
    db = sqlite3.connect("bancodedados/tkartic.db")
    cursor = db.cursor()

    while True:
        try:
            data = conn.recv(1024).decode()
            if not data:
                break  # cliente fechou a conexão

            print(f"Recebi query de {addr}: {data}")

            try:
                cursor.execute(data)

                # Se for um comando de escrita, faz commit
                if data.strip().lower().startswith(("insert", "update", "delete", "create", "drop")):
                    db.commit()
                    conn.sendall(b"OK")  # resposta simples de sucesso
                else:
                    rows = cursor.fetchall()
                    conn.sendall(json.dumps(rows).encode())

            except Exception as e:
                conn.sendall(f"Erro: {e}".encode())

        except ConnectionResetError:
            print(f"Cliente {addr} desconectou à força.")
            break

    db.close()
    conn.close()
    print(f"Conexão encerrada com {addr}")

def tcp_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen(5)
    print(f"Servidor rodando em {HOST}:{PORT}")

    while True:
        conn, addr = server.accept()
        client_thread = threading.Thread(target=handle_client, args=(conn, addr))
        client_thread.start()

def broadcaster():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    while True:
        message = f"TKARTIC_SERVER;{HOST};{PORT}"
        sock.sendto(message.encode(), (BROADCAST_IP, BROADCAST_PORT))
        print("Anúncio enviado:", message)
        time.sleep(5)  # envia a cada 5 segundos

def main():
    # inicia o servidor TCP em uma thread
    tcp_thread = threading.Thread(target=tcp_server, daemon=True)
    tcp_thread.start()

    # inicia o broadcaster UDP na thread principal
    broadcaster()

if __name__ == "__main__":
    main()