import config
from dbinstances import Student, Question
from math import exp

# Расчет доли баллов за быстроту реакции
# time - время ответа в часах
def waiting_func(time: int):
    return exp(-config.HALF_WAITING_FACTOR * time)

# Расчет доли баллов за быстроту ответа
# time - время ответа в секундах
# good_time - время ответа в секундах, за которое получаешь 90%
def answr_func(time: int, good_time: int):
    return 9 * good_time / (time + 9 * good_time)

# Формула расчета суммарного кол-ва баллов за ответ (учитывающая все характеристики)
# q_cmplx - сложность вопроса (question complexity)
# t1 - время ожидания готовности
# t2 - время ответа
# good_t2 - хорошее время ответа (на 90%)
# atmpt - номер попытки
def formula(q_cmplx: int, t1: int, t2: int, atmpt: int, good_t2: int):
    return 100 / atmpt * (config.WAITING_FACTOR * waiting_func(t1) + config.ANSWR_TIME_FACTOR * answr_func(t2, good_t2)) * (1 - config.CMPLXITY_FACTOR * q_cmplx)

# Расчет баллов для студента stdnt, при ответе на вопрос qstn, i-ый раз (по умолчанию - последний)
def answer_summary(stdnt: Student, qstn: Question, i=-1):
    return formula(qstn.first_to_answer / qstn.total_answers, stdnt.data[qstn.number]['right'][i][0], student.data[qstn.number]['right'][i][1], len(stdnt.data['right']) + stdnt.data['wrong'], qstn.best_time_to_answer)

# Возвращает отсортированный массив кортежей-пар (nickname, summary)
def get_rating():
    rating = dict()
    for student in Student.objects():
        summary = 0
        for question in Question.objects():
            for i in range(len(student.data[question.number])):
                summary += answer_summary(student, question, i)
        rating[student.tg_login] = summary
    return sorted(rating.items(), key=lambda x:x[1])
