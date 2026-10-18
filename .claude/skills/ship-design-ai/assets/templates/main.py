from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI(title='Ship Design AI')

class HullInput(BaseModel):
    length_pp: float = Field(gt=0)
    beam: float = Field(gt=0)
    draft: float = Field(gt=0)
    block_coefficient: float = Field(gt=0, le=1)

@app.post('/api/design/evaluate')
def evaluate(data: HullInput):
    volume = data.length_pp * data.beam * data.draft * data.block_coefficient
    return {'volume_m3': round(volume, 3), 'displacement_tonnes': round(volume * 1.025, 3), 'note': 'educational estimate'}
