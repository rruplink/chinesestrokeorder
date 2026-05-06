from pydantic import BaseModel, Field

MAX_CARDS_PER_DECK = 250


class DeckRequest(BaseModel):
    deckName: str = Field(default="Chinese Stroke Order", min_length=1, max_length=120)
    lines: list[str] = Field(min_length=1, max_length=MAX_CARDS_PER_DECK)


class PreviewCard(BaseModel):
    hanzi: str
    pinyin: str
    definition: str
    missingStrokeChars: list[str]
    needsAiLookup: bool


class CostEstimate(BaseModel):
    detectedCards: int
    aiAssistedCards: int
    estimatedUsd: float
    bufferEstimateUsd: str
    note: str


class PreviewResponse(BaseModel):
    deckName: str
    cards: list[PreviewCard]
    cost: CostEstimate
    warnings: list[str]
