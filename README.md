# GustavoTube v2.0

Foi criado com o objetivo de facilitar o download de vídeos e áudios do Youtube.

### Como Instalar

É necessário ter o [Python](https://www.python.org/downloads/) na versão 3.11+

```py
python ^= 3.11
```

Realize o clone do repositório e acesse o diretório da aplicação

```
git clone https://github.com/edvitor13/gustavotube
```

```
cd gustavotube
```

No diretório clonado do projeto instale via PIP o arquivo de `requirements.txt`

```py
python -m pip install -r requirements.txt
```

Ou caso tenha [Poetry](https://python-poetry.org/docs/)

```py
poetry install
```

### Dependências

Para o funcionamento compleoto, principalmente para gerar mp3, o GustavoTube necessita que o `FFMPEG` esteja instalado em sua máquina.

FFmpeg é um software livre e de código aberto usado para converter e manipular arquivos de áudio e vídeo via linha de comando.

Link de Download: https://ffmpeg.org/download.html

- Como instalar no `Windows`: https://pt.wikihow.com/Instalar-o-FFmpeg-no-Windows
- Como instalar no `Linux`: https://www.hostinger.com.br/tutoriais/como-instalar-ffmpeg
- Como instalar no `MacOS`: https://www.youtube.com/watch?v=8nbuqYw2OCw

Para verificar se realmente está instalado envie o seguinte comando no terminal:

```python
ffmpeg -version
```

### Como utilizar

1. Com tudo devidamente instalado, no diretório da aplicação envie o comando:

    ```py
    python main.py
    ```

2. Será aberta uma janela solicitando que você informe a url do vídeo do youtube que deseja baixar.
    
3. Escolha se baixará mp4 ou mp3.
    
4. Selecione a resolução se for MP4 ou a qualidade do áudio se for MP3.
    
5. Clique no botão baixar e escolha onde deseja salvar o vídeo/audio que será baixado.

6. Aguarde o download finalizar e verifique se realmente foi baixado.