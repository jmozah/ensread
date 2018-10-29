import sys
import yaml
from ensread import Ensread

if __name__ == "__main__":
    try:
        if len(sys.argv) != 2:
            print 'Usage: python main.py <config path>'
            sys.exit(-1)
        configFile = sys.argv[1]
        with open(configFile, 'r') as f:
            config = yaml.load(f)
        Ensread(config)
    except Exception, e:
        print(e.message)
        sys.exit(-1)


