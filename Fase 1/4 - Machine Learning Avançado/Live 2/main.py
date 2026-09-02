#python3 -m venv ./venv/

#source ./venv/bin/activate

# python3 -m pip install --upgrade pip

#pip install "fastapi[standard]"
#fastapi dev main.py

#pip install scikit-learn


from typing import Union
import pickle

from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/ml/classification/")
def make_predict(
    daily_time_spent_on_site,
    age,
    area_income,
    daily_internet_usage
):
    
    model = pickle.load(open("model_latest.pkl", "rb"))

    novo_input = [[
        float(daily_time_spent_on_site),
        int(age),
        float(area_income),
        float(daily_internet_usage)
    ]]

    _predict = model.predict(novo_input)
    _predict = str(_predict[0])


    return {
        "output": _predict
    }