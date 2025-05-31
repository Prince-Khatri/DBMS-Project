from flask import Flask,render_template
from flask_sqlalchemy import SQLAchemy
from datetime import datetime


app=Flask(__name__)


app.config["SQLALCHEMY_DATABASR_URI"]="sqlite:///todo.db"
app.config["SQLALCHEMY_TRACK_MODIFICATION"]=False
db=SQLAlchemy(app)

class todo(db.Model):
	sno=db.Column(db.Integer,primary_key=True)
	title=db.Column(db.String(200),nullable=False)
	desc=db.Column(db.String(500),nullable=False)
	dateCreated=db.Column(db.DateTime,default=datetime.utcnow)

	def __repr__(self) -> str:
		return f"{self.sno} - {self.title}"
@app.route('/')
def helloWorld():
	return render_template("index.html")

@app.route('/products')
def products():
	return "This is a product"

if __name__=="__main__":
	app.run(debug=True,port=8000)
