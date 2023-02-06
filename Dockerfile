FROM public.ecr.aws/lambda/python:3.9.16

COPY . ./
CMD ["app.headers"]