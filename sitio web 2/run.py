import os
import webbrowser
from threading import Timer
from app import app

if __name__ == '__main__':
    port=int(os.environ.get('PORT','8000'))
    url=f'http://127.0.0.1:{port}/'
    Timer(1.0, lambda: webbrowser.open(url)).start()
    print(f'Costa Rica Urban Home running at {url}')
    app.run(host='127.0.0.1', port=port, debug=False)
