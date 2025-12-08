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
        except OSError:
            break
    return buffer

def deploy_app():
    pid, fd = pty.fork()
    
    if pid == 0:
        # Child process
        # Using sshpass if available would be easier, but sticking to pty for consistency with previous success
        # But wait, User enabled password auth, so I can just use the previous method.
        # Actually, now that password auth is enabled, I can just standard ssh command? 
        # No, I still need to pass the password.
        os.execvp("ssh", ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "PreferredAuthentications=password", "-o", "PubkeyAuthentication=no", "root@162.43.33.37"])
    else:
        # Parent process
        try:
            # Wait for password prompt
            print("Waiting for password prompt...")
            read_until(fd, "password:")
            
            # Send password
            print("Sending password...")
            os.write(fd, b"@hN5keQGc\n")
            
            # Wait for prompt explicitly because MOTD is long
            print("Waiting for shell prompt...")
            # Wait for commonly used root prompt end characters
            # The output showed "root@x162-43-33-37:~#"
            read_until(fd, "~#")
            print("Prompt found!")
            
            time.sleep(1)
            
            # Send commands
            # 1. Clone or Pull repo
            # 2. Setup .env
            # 3. Docker Compose Up
            commands = [
                "echo 'Starting deployment...'",
                "cd /opt",
                # Check if directory exists, if not clone, else pull
                "if [ ! -d '/opt/ansistem' ]; then git clone https://github.com/hirohiroko250/ansistem.git; else cd ansistem && git pull; fi",
                "cd /opt/ansistem",
                
                # Copy example env if .env doesn't exist (basic setup)
                # In a real scenario, we might want to inject secrets here, but for now we use the example values as per plan
                "if [ ! -f '.env' ]; then cp .env.example .env; fi",
                
                # Build and Up
                "docker compose up -d --build",
                
                # Check running
                "docker compose ps",
                "exit"
            ]
            
            for cmd in commands:
                print(f"Sending command: {cmd}")
                os.write(fd, f"{cmd}\n".encode())
                if "docker compose up" in cmd:
                    # Build might take a long time
                    print("Waiting for build (this may take 5-10 minutes)...")
                    # We can't really just sleep blindly for 10 mins, but for this pty script hack it's the safest simple way
                    # Better would be to read output until it finishes, but build output is verbose.
                    # Let's give it a generous sleep and rely on the user checking if it hangs.
                    # Or better - just don't exit immediately and let the read loop show output?
                    # But the read loop is below.
                    # So sending the command is fine. 
                    # The issue is the next command 'docker compose ps' might fire too early if I don't wait.
                    # But 'up -d' runs in detached, so the build happens in foreground then returns?
                    # Yes, 'up -d --build' waits for build then detach. 
                    # So prompt won't return until built.
                    # So I don't need explicit sleep for the command to finish, 
                    # BUT I need to wait before sending the NEXT command?
                    # os.write allows typing ahead in pty? Yes usually. 
                    # But if buffer fills up it might block?
                    # Let's just wait a bit.
                    pass
                else:
                    time.sleep(1)
            
            # Read remaining output until EOF
            print("Reading output...")
            while True:
                try:
                    chunk = os.read(fd, 1024)
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
    deploy_app()
