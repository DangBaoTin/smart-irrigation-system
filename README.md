<<<<<<< HEAD
## Install and activate virtual environment
- Init virt env:
```bash
python3 -m venv venv
virtualenv -p /Library/Frameworks/Python.framework/Versions/3.9/bin/python3.9 venv
```
- Activate virtual environment:
```bash
source venv/bin/activate
```
- Install `requirements.txt` for the required libraries:
```bash
pip install -r requirements.txt
```
- To delete any unnecessary libraries:
```bash
pip uninstall <package-name>
```
- To deactivate virtual environment:
```bash
deactivate
rm -rf venv
```
=======
## Install and activate virtual environment
- Init virt env:
```bash
python3 -m venv venv
virtualenv -p /Library/Frameworks/Python.framework/Versions/3.9/bin/python3.9 venv
```
- Activate virtual environment:
```bash
source venv/bin/activate
```
- Install `requirements.txt` for the required libraries:
```bash
pip install -r requirements.txt
```
- To delete any unnecessary libraries:
```bash
pip uninstall <package-name>
```
- To deactivate virtual environment:
```bash
deactivate
rm -rf venv
```

## Temporary flow
env = VirtualGarrden(...)

While on:

data -> env

env ->  + database (do không gọi env.step() nên action sẽ là Null)
        
        + lưu buffer để xử lý

agent (đã load) gọi hàm env.step(lấy bao nhiêu trước đó, gọi từ cái db) -> action -> lưu database -> tính score

next step
>>>>>>> ec7210dbf662ae639d02953e6df7bdc427636340
