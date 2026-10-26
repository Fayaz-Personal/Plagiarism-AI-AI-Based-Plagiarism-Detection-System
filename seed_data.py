"""
Sample demonstration data generator for PlagiarismAI.
Synthesizes realistic academic texts for demonstration and runs genuine analysis.
"""
from pathlib import Path
from datetime import datetime, timezone

from extensions import db
from models.document_models import Document, Setting
from plagiarism.plagiarism_engine import analyze_document
from plagiarism.preprocessing import segment_sentences

SAMPLE_REF_A = """Artificial intelligence and machine learning have transformed modern computational research across diverse scientific disciplines.
Machine learning algorithms identify complex statistical patterns within vast datasets to formulate predictive mathematical models.
Supervised learning requires labeled training datasets where the algorithm iteratively minimizes an empirical loss function through gradient descent.
Deep neural networks utilize multiple hidden layers of interconnected artificial neurons to extract hierarchical representations of input data.
Convolutional neural networks excel at extracting spatial feature representations from high-dimensional image data.
Recurrent neural architectures process sequential temporal data by preserving internal hidden states across successive time steps.
Transfer learning enables pre-trained foundational models to adapt to novel downstream domain tasks with minimal labeled target examples."""

SAMPLE_REF_B = """Renewable energy infrastructure plays an essential role in mitigating global anthropogenic climate change and reducing carbon emissions.
Photovoltaic solar panels convert incident solar irradiance directly into electrical energy through the physical photovoltaic effect in silicon semiconductors.
Wind turbines harness atmospheric kinetic energy to rotate aerodynamic blades connected to electromagnetic mechanical generators.
Energy storage systems, including grid-scale lithium-ion battery banks, resolve the intermittent generation profile of solar and wind generation sources.
Decarbonizing industrial heating and long-distance transportation remains a primary engineering challenge in transitioning toward net-zero emissions.
International climate agreements establish enforceable carbon reduction targets to limit global average surface temperature increase within two degrees Celsius."""

SAMPLE_REF_C = """Relational database management systems organize data into structured two-dimensional relations consisting of rows and columns.
Structured Query Language provides a standardized declarative paradigm for querying, updating, and administering relational databases.
Database transactions must satisfy the foundational ACID guarantees: atomicity, consistency, isolation, and durability.
B-tree and hash indexing mechanisms dramatically accelerate retrieval efficiency by reducing the computational cost of disk block read operations.
Normalization theory applies rigorous functional dependencies to eliminate data redundancy and prevent anomalous insert, update, and delete side-effects.
Concurrency control algorithms utilize two-phase locking and multi-version concurrency control to maintain serializable execution schedules."""

SAMPLE_SUBMITTED = """In this research paper, we investigate the modern evolution of intelligent autonomous computational systems.
Artificial intelligence and machine learning have transformed modern computational research across diverse scientific disciplines.
Researchers have demonstrated that machine learning algorithms identify complex statistical patterns within vast datasets to formulate predictive mathematical models.
Our experimental methodology applied custom neural network architectures to benchmark evaluation suites.
Deep neural networks utilize multiple hidden layers of interconnected artificial neurons to extract hierarchical representations of input data.
Furthermore, transfer learning enables pre-trained foundational models to adapt to novel downstream domain tasks with minimal labeled target examples.
In conclusion, automated representation learning provides remarkable empirical advantages over legacy rule-based expert systems."""


def seed_sample_data(app):
    """Creates sample reference documents and a submitted document, then analyzes it."""
    with app.app_context():
        # Check if already seeded to prevent duplicates
        existing_ref_a = Document.query.filter_by(original_filename="Ref_AI_Foundations.txt").first()
        if existing_ref_a:
            return "Sample demonstration documents already exist in the database."

        upload_dir = Path(app.config['UPLOAD_FOLDER'])
        upload_dir.mkdir(parents=True, exist_ok=True)

        docs_to_create = [
            ("Ref_AI_Foundations.txt", SAMPLE_REF_A, "reference"),
            ("Ref_Climate_Renewable_Energy.txt", SAMPLE_REF_B, "reference"),
            ("Ref_Relational_Databases.txt", SAMPLE_REF_C, "reference"),
            ("Submitted_AI_Survey_Student_Paper.txt", SAMPLE_SUBMITTED, "submitted"),
        ]

        created_docs = []
        for filename, content, doc_type in docs_to_create:
            stored_name = f"seed_{filename}"
            file_path = upload_dir / stored_name
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            file_size = os.path.getsize(file_path)
            sentences = segment_sentences(content)
            word_count = len(content.split())

            doc = Document(
                original_filename=filename,
                stored_filename=stored_name,
                file_type="txt",
                file_size=file_size,
                document_type=doc_type,
                extracted_text=content,
                word_count=word_count,
                sentence_count=len(sentences),
                upload_date=datetime.now(timezone.utc),
                processing_status="processed",
                is_active=True
            )
            db.session.add(doc)
            db.session.flush()
            created_docs.append(doc)

        db.session.commit()

        # Find the submitted document and run analysis through the genuine engine
        submitted_doc = next(d for d in created_docs if d.document_type == "submitted")
        analysis = analyze_document(submitted_doc.id)

        return f"Successfully generated 3 reference documents and analyzed '{submitted_doc.original_filename}' (Analysis #{analysis.id}, Highest Similarity: {analysis.highest_similarity_score:.1f}%)."


if __name__ == '__main__':
    from app import create_app
    app = create_app()
    msg = seed_sample_data(app)
    print(msg)
