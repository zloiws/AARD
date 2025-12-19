from app.core.database import engine
from sqlalchemy import inspect


def main():
    ins = inspect(engine)
    idxs = ins.get_indexes('execution_traces')
    print(idxs)

if __name__ == '__main__':
    main()


