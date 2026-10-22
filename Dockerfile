# 1. ოფიციალური Python-ის კომპაქტური იმიჯი
FROM python:3.10-slim

# 2. სამუშაო დირექტორიის შექმნა კონტეინერში
WORKDIR /app

# 3. დამოკიდებულებების გადაწერა და ინსტალაცია
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. მთლიანი პროექტის კოდის გადაწერა
COPY . .

# 5. პორტი, რომელზეც API იტვირთება
EXPOSE 8000

# 6. Uvicorn სერვერის გაშვება
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]