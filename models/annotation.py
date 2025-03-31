from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass
class Annotation:
    coords: List[float]
    text: str
    ratio: float
    rect: int
    text_id: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            'coords': self.coords,
            'text': self.text,
            'ratio': self.ratio,
            'rect': self.rect,
            'text_id': self.text_id
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Annotation':
        return cls(
            coords=data['coords'],
            text=data['text'],
            ratio=data['ratio'],
            rect=data['rect'],
            text_id=data['text_id']
        )
