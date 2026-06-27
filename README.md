# لوحة تحليل التشغيل والتكلفة

تطبيق Streamlit لتحليل بيانات الرحلات والسائقين والوجهات من ملف Excel أو CSV، بهدف فهم أثر التشغيل على التكلفة واتخاذ قرارات أسرع.

## فكرة المشروع

اللوحة تعرض:

- ملخصًا تنفيذيًا
- مقارنة بين السائقين
- تحليلًا ماليًا للوجهات والرحلات
- مؤشرات تنبيه للرحلات التي تحتاج مراجعة تحليلية
- تنزيل البيانات المفلترة

## التشغيل المحلي

```bash
pip install -r requirements.txt
streamlit run app.py
```

## النشر على GitHub وStreamlit Cloud

1. ارفع الملفات التالية إلى GitHub:
   - `app.py`
   - `requirements.txt`
   - `README.md`
   - `.streamlit/config.toml`
2. افتح [Streamlit Community Cloud](https://streamlit.io/cloud).
3. اربط حساب GitHub.
4. اختر المستودع.
5. اجعل الملف الرئيسي `app.py`.
6. اضغط `Deploy`.

## هيكل المشروع

```text
repo/
├─ app.py
├─ requirements.txt
├─ README.md
└─ .streamlit/
   └─ config.toml
```

## ملاحظات

- التطبيق يكتشف الأعمدة العربية والإنجليزية تلقائيًا.
- لو تغير اسم العمود قليلًا، يحاول التطبيق العثور عليه تلقائيًا.
- الملف الحالي مناسب جدًا لملف `apr-june.xlsx`.
