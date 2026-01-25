from TTS.utils.manage import ModelManager
import argparse
from os import environ,mkdir
from os.path import exists

manager = ModelManager()

def install_models(model):
    environ['TTS_HOME'] = "./models/"
    if not exists("./models/"):
        mkdir("./models/")
    try:
        ModelManager.download_model(model_name=model)
    except Exception as e:
        print(e)

def reove_models(model):
    pass

def generate_TTS(model,text):
    pass

def list_from_web():
    pass

def config_source(URL):
    pass
parser = argparse.ArgumentParser(description="TTS Manager")
subparser = parser.add_subparsers(dest="command")

#Install Models
InstallParser = subparser.add_parser("install", help="Install a model")
InstallParser.add_argument("ModelName")
InstallParser.set_defaults(function=install_models)

#Remove Models
RemoveParser = subparser.add_parser("remove", help="Remove a model")
RemoveParser.add_argument("ModelName")
RemoveParser.set_defaults(function=reove_models)

#Generate with a local model and output it into a WAV file
PlayParser = subparser.add_parser("play", help="Generate WAV with a sepcific model")
PlayParser.add_argument("ModelName", "Text")
PlayParser.set_defaults(function=generate_TTS)

#list TTS models enabled on the web server
ListWebParser = subparser.add_parser("list", help="List the Models enable on the web")
ListWebParser.add_argument("")
ListWebParser.set_defaults(function=list_from_web)

#Enable Users to change the source to foster the download speed
SourceParser = subparser.add_parser("source", help="Change the download source")
SourceParser.add_argument("SourceURL")
SourceParser.set_defaults(function=config_source)
