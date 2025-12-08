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

def test_conn():
    pid, fd = pty.fork()
    
    if pid == 0:
        os.execvp("ssh", ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "PreferredAuthentications=password", "-o", "PubkeyAuthentication=no", "root@162.43.33.37", "echo 'SUCCESS_LOGIN'"])
    else:
        try:
            print("Waiting for password prompt...")
            read_until(fd, "password:")
            
            print("Sending password...")
            os.write(fd, b"@hN5keQGc\n")
            
            while True:
                try:
                    chunk = os.read(fd, 1024)
                    if not chunk: break
                    sys.stdout.buffer.write(chunk)
                    sys.stdout.flush()
                except OSError:
                    break
        finally:
            os.close(fd)
            os.waitpid(pid, 0)

if __name__ == "__main__":
    test_conn()
