import pty
import os
import sys
import time

def read_until(fd, marker):
    buffer = b""
    while True:
        try:
            chunk = os.read(fd, 1024)
            if not chunk:
                break
            buffer += chunk
            sys.stdout.buffer.write(chunk)
            sys.stdout.flush()
            if marker.encode() in buffer:
                return buffer
            if b"Permission denied" in buffer:
                return buffer
        except OSError:
            break
    return buffer

def provision_server():
    pid, fd = pty.fork()
    
    if pid == 0:
        # Child process
        # Force password authentication
        os.execvp("ssh", ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "PreferredAuthentications=password", "-o", "PubkeyAuthentication=no", "root@162.43.33.37"])
    else:
        # Parent process
        try:
            # Wait for password prompt
            print("Waiting for password prompt...")
            output = read_until(fd, "password:")
            
            if b"Permission denied" in output:
                print("\n\nPassword authentication is disabled on the server or failed.")
                return

            # Send password
            print("Sending password...")
            os.write(fd, b"@hN5keQGc\n")
            
            time.sleep(5)
            
            # Send commands
            commands = [
                "echo 'Connection established'",
                "export DEBIAN_FRONTEND=noninteractive",
                "apt-get update",
                "apt-get install -y git",
                "curl -fsSL https://get.docker.com -o get-docker.sh",
                "sh get-docker.sh",
                "docker compose version",
                "exit"
            ]
            
            for cmd in commands:
                print(f"Sending command: {cmd}")
                os.write(fd, f"{cmd}\n".encode())
                if "apt-get" in cmd or "get-docker" in cmd:
                    time.sleep(30) 
                else:
                    time.sleep(2)
                    
            # Read remaining output
            while True:
                try:
                    chunk = os.read(fd, 1024)
                    try:
                        # Attempt to interpret exit status if possible, 
                        # but simple read is enough for log.
                        pass
                    except: 
                       pass
                       
                    if not chunk: break
                    sys.stdout.buffer.write(chunk)
                    sys.stdout.flush()
                except OSError:
                    break
                    
        except Exception as e:
            print(f"Error: {e}")
        finally:
            os.close(fd)
            os.waitpid(pid, 0)

if __name__ == "__main__":
    provision_server()
