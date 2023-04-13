import sys
from os.path import dirname

sys.path.append(dirname(dirname(__file__)))


from zonda.main import main


main()
