#!/usr/bin/env python3
from __future__ import annotations
from app.core.database import Base, engine
import app.models  # register all models with Base metadata

def main():
    print("Creating all tables from models...")
    Base.metadata.create_all(bind=engine)
    print("Done")

if __name__ == '__main__':
    main()


