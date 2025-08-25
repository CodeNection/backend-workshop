from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, ForeignKey
from sqlalchemy.orm import sessionmaker, relationship, declarative_base, Session

# --------------------------
# Database Setup
# --------------------------

# SQLite database file
DATABASE_URL = "sqlite:///./app.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

# Base class for database models
Base = declarative_base()

# --------------------------
# Database Models
# --------------------------

class Project(Base):
    """Database model for projects"""
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    project_name = Column(String, index=True)
    project_description = Column(String)

    # A project can have many students
    students = relationship("Student", back_populates="project")


class Student(Base):
    """Database model for students"""
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    linkedin_profile = Column(String, nullable=True)
    about_you = Column(String, nullable=True)
    specialisation = Column(String, nullable=True)
    cgpa = Column(Float, nullable=True)
    favourite_language = Column(String, nullable=True)
    favourite_framework = Column(String, nullable=True)
    is_leader = Column(Boolean, default=False)

    # Each student may belong to a project
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)

    # Relationship back to project
    project = relationship("Project", back_populates="students")


# --------------------------
# Pydantic Schemas (for validation and responses)
# --------------------------

# Project schemas
class ProjectBase(BaseModel):
    project_name: str
    project_description: str

class ProjectSchema(ProjectBase):
    id: int
    class Config:
        orm_mode = True


# Student schemas
class StudentBase(BaseModel):
    name: str
    email: str
    linkedin_profile: Optional[str] = None
    about_you: Optional[str] = None
    specialisation: Optional[str] = None
    cgpa: Optional[float] = None
    favourite_language: Optional[str] = None
    favourite_framework: Optional[str] = None
    is_leader: bool = False
    project_id: Optional[int] = None

class StudentSchema(StudentBase):
    id: int
    class Config:
        orm_mode = True


# --------------------------
# FastAPI app
# --------------------------

app = FastAPI()

# Create database tables if not exist
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --------------------------
# Project Endpoints
# --------------------------

@app.post("/projects/", response_model=ProjectSchema, status_code=201)
def create_project(project: ProjectBase, db: Session = Depends(get_db)):
    new_project = Project(**project.model_dump())
    db.add(new_project)
    db.commit()
    db.refresh(new_project)
    return new_project

@app.get("/projects/", response_model=List[ProjectSchema])
def list_projects(db: Session = Depends(get_db)):
    return db.query(Project).all()

@app.get("/projects/{project_id}", response_model=ProjectSchema)
def get_project(project_id: int, db: Session = Depends(get_db)):
    project = db.query(Project).get(project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    return project

@app.put("/projects/{project_id}", response_model=ProjectSchema)
def update_project(project_id: int, updated: ProjectBase, db: Session = Depends(get_db)):
    project = db.query(Project).get(project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    project.project_name = updated.project_name
    project.project_description = updated.project_description
    db.commit()
    db.refresh(project)
    return project

@app.delete("/projects/{project_id}", status_code=204)
def delete_project(project_id: int, db: Session = Depends(get_db)):
    project = db.query(Project).get(project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    for student in project.students:
        student.project_id = None

    db.delete(project)
    db.commit()
    return {"message": "Project deleted successfully"}

@app.get("/project_students/{project_id}")
def list_projects_with_students(project_id: int, db: Session = Depends(get_db)):
    project = db.query(Project).get(project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    
    project.students
    return project

# --------------------------
# Student Endpoints
# --------------------------

@app.post("/students/", response_model=StudentSchema, status_code=201)
def create_student(student: StudentBase, db: Session = Depends(get_db)):
    # If a project_id is given, check if it exists
    if student.project_id is not None:
        if not db.query(Project).get(student.project_id):
            raise HTTPException(400, f"Project {student.project_id} does not exist")

    new_student = Student(**student.model_dump())
    db.add(new_student)
    db.commit()
    db.refresh(new_student)
    return new_student

@app.get("/students/")
def list_students(db: Session = Depends(get_db)):
    return db.query(Student).all()

@app.get("/students/{student_id}", response_model=StudentSchema)
def get_student(student_id: int, db: Session = Depends(get_db)):
    student = db.query(Student).get(student_id)
    if not student:
        raise HTTPException(404, "Student not found")
    return student

@app.put("/students/{student_id}", response_model=StudentSchema)
def update_student(student_id: int, updated: StudentBase, db: Session = Depends(get_db)):
    student = db.query(Student).get(student_id)
    if not student:
        raise HTTPException(404, "Student not found")

    if updated.project_id is not None:
        if not db.query(Project).get(updated.project_id):
            raise HTTPException(400, f"Project {updated.project_id} does not exist")

    for field, value in updated.model_dump().items():
        setattr(student, field, value)

    db.commit()
    db.refresh(student)
    return student

@app.delete("/students/{student_id}", status_code=204)
def delete_student(student_id: int, db: Session = Depends(get_db)):
    student = db.query(Student).get(student_id)
    if not student:
        raise HTTPException(404, "Student not found")
    db.delete(student)
    db.commit()
    return {"message": "Student deleted successfully"}

