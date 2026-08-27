from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
import joblib 

TRAINING_DATA = [
    ("Dedication", "front"),
    ("Foreword", "front"),
    ("Preface", "front"),
    ("Introduction", "front"),
    ("Copyright", "front"),
    ("Acknowledgements", "front"),
    ("Contents", "front"),

    ("Chapter 1", "chapter"),
    ("Chapter 2", "chapter"),
    ("1", "chapter"),
    ("2", "chapter"),
    ("Chapter Three", "chapter"),
    ("The Journey Begins", "chapter"),
    ("Winter", "chapter"),
    ("The Last Stand", "chapter"),
    ("1939-1958", "chapter"),
    ("1972-1974", "chapter"),
    ("1964", "chapter"),
    ("1968", "chapter"),
    ("A year and a half later", "chapter"),

    ("Appendix", "back"),
    ("Bibliography", "back"),
    ("References", "back"),
    ("About the Author", "back"),
    ("What's next on your reading list?", "back"),
]

class SectionClassifier:
    def __init__(self):
        titles = [row[0] for row in TRAINING_DATA]
        labels = [row[1] for row in TRAINING_DATA]

        self.model = Pipeline([
            (
                "tfidf",
                TfidfVectorizer(
                    lowercase=True,
                    ngram_range=(1, 2),
                ),
            ),
            ("clf", LogisticRegression(),),
        ])

        self.model.fit(titles, labels,)

    def predict(self, title):
        return self.model.predict([title])[0]