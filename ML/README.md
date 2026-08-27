# Machine Learning Components
This directory contains experimental machine learning components used by the EPUB Reader application. \
The current focus is document structure analysis, specifically identifying whether EPUB sections belong to the front matter, main content, or back matter of a book.

## Overview
The current implementation uses:

- TF-IDF vectorization
- Logistic Regression classification
- Scikit-learn pipelines

Section titles are used as input features and are classified into one of three categories:

| Category | Examples |
|-----------|----------|
| front | Dedication, Foreword, Preface, Introduction |
| chapter | Chapter 1, Winter, The Journey Begins |
| back | Appendix, Bibliography, References, About the Author |

## Files

### `section_classifier.py`
Contains the application's active section classifier.

Features:
- Trains a Logistic Regression model at runtime
- Uses TF-IDF vectorization with unigram and bigram features
- Predicts whether a section belongs to:
  - Front Matter
  - Chapter Content
  - Back Matter

Example:

```python
classifier = SectionClassifier()

classifier.predict("Dedication")
# front

classifier.predict("Chapter 12")
# chapter

classifier.predict("Bibliography")
# back
```

### `train_classifier.py`
Example training script used to create and serialize a trained model.

This script demonstrates:

- Building a Scikit-learn pipeline
- Training a Logistic Regression classifier
- Persisting the model with Joblib

Output:

```text
trained_model.pkl
```

## Technologies
- Python
- Scikit-learn
- TF-IDF Vectorization
- Logistic Regression
- Joblib

## Future Work

Potential machine learning and NLP enhancements include:

- Improved Front Matter / Back Matter classification
- Automatic chapter classification
- Genre prediction
- Metadata extraction and enrichment
- Character extraction
- Topic modeling
- Semantic search
- Recommendation systems
- AI-assisted summarization

## Notes

This directory serves as an experimentation area for applying Machine Learning and Natural Language Processing techniques to EPUB document analysis. The current classifier is intentionally lightweight and designed to demonstrate practical ML integration within a desktop application.