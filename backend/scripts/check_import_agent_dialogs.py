import importlib
import traceback


def main():
    try:
        m = importlib.import_module('app.api.routes.agent_dialogs')
        print('imported:', m)
    except Exception:
        traceback.print_exc()

if __name__ == '__main__':
    main()


