# 📰 Buscador de Notícias — Scraper
### Sistema de monitoramento de notícias em tempo real via Google News RSS · Real-time news monitoring system using Google News RSS scraping

---

## 🇧🇷 Português

### Sobre o projeto
Sistema que monitora notícias em tempo real a partir do Google News RSS. Você cadastra temas de interesse e o sistema busca automaticamente as notícias mais recentes, salvando tudo em um banco de dados e expondo via API REST.

### Como funciona
```
Tema cadastrado → Coletor busca no Google News RSS
→ feedparser lê o XML → Notícias salvas no banco
→ API retorna os dados → Dashboard exibe as notícias
```

### Tecnologias utilizadas
| Tecnologia | Função |
|------------|--------|
| Python 3.13 | Linguagem principal |
| FastAPI | API REST |
| SQLAlchemy | ORM / Banco de dados |
| SQLite | Banco de dados local |
| feedparser | Leitura do feed RSS |
| APScheduler | Agendamento da coleta |
| Uvicorn | Servidor ASGI |
| Docker | Containerização |
| AWS ECR | Repositório de imagens Docker |
| AWS ECS Fargate | Execução dos containers |
| AWS ALB | Load Balancer |

### Estrutura do projeto
```
backend_scraper/
├── main.py              → API REST + agendador automático
├── collector.py         → Coletor de notícias via RSS
├── database.py          → Configuração do banco de dados
├── models.py            → Tabelas: Topic e News
├── Dockerfile           → Receita para containerização
├── task-definition.json → Configuração do ECS
├── requirements.txt     → Dependências do projeto
└── .env                 → Variáveis de ambiente (não sobe pro git)
```

### Endpoints da API
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/topics` | Lista todos os temas |
| POST | `/topics` | Cadastra um novo tema |
| PATCH | `/topics/{id}` | Atualiza um tema |
| DELETE | `/topics/{id}` | Remove um tema |
| GET | `/news` | Lista as notícias coletadas |
| GET | `/news?topic_id=1` | Filtra notícias por tema |
| POST | `/collect` | Dispara coleta manual |
| GET | `/news/count` | Contagem de notícias por tema |

---

## 🚀 Como rodar localmente

**1. Clone o repositório**
```bash
git clone https://github.com/Karlmalone13/Buscador-de-noticias---Scraper-.git
cd Buscador-de-noticias---Scraper-/backend_scraper
```

**2. Crie e ative o ambiente virtual**
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate
```

**3. Instale as dependências**
```bash
pip install -r requirements.txt
pip install feedparser
```

**4. Suba a API**
```bash
uvicorn main:app --reload
```

**5. Acesse a documentação interativa**
```
http://localhost:8000/docs
```

**6. Cadastre um tema**
```json
POST /topics
{
  "name": "Escala 6x1",
  "query": "escala 6x1"
}
```

---

## ☁️ Deploy na AWS com ECS Fargate + Load Balancer

### Pré-requisitos
- Docker Desktop instalado
- AWS CLI instalado e configurado (`aws configure`)
- Conta AWS com permissões: ECS, ECR, IAM, EC2, ELB, CloudWatch

### Arquitetura
```
Usuário → Load Balancer (porta 80)
        → Target Group
        → 3 containers ECS Fargate
        → Cada container roda a API Python
```

### Passo a passo completo

**1. Build da imagem Docker**
```bash
docker build -t buscador-noticias .
```

**2. Criar repositório no ECR**
```bash
aws ecr create-repository --repository-name buscador-noticias --region sa-east-1
```

**3. Login no ECR**
```bash
aws ecr get-login-password --region sa-east-1 | docker login --username AWS --password-stdin SEU_ACCOUNT_ID.dkr.ecr.sa-east-1.amazonaws.com
```

**4. Tag e push da imagem**
```bash
docker tag buscador-noticias:latest SEU_ACCOUNT_ID.dkr.ecr.sa-east-1.amazonaws.com/buscador-noticias:latest
docker push SEU_ACCOUNT_ID.dkr.ecr.sa-east-1.amazonaws.com/buscador-noticias:latest
```

**5. Criar cluster ECS**
```bash
aws ecs create-cluster --cluster-name buscador-cluster --region sa-east-1
```

**6. Criar role IAM para o ECS**
```bash
aws iam create-role --role-name ecsTaskExecutionRole \
  --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"ecs-tasks.amazonaws.com"},"Action":"sts:AssumeRole"}]}'

aws iam attach-role-policy --role-name ecsTaskExecutionRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy
```

**7. Criar grupo de logs**
```bash
aws logs create-log-group --log-group-name /ecs/buscador-noticias --region sa-east-1
```

**8. Registrar task definition**
```bash
aws ecs register-task-definition --cli-input-json file://task-definition.json --region sa-east-1
```

**9. Pegar VPC e subnets padrão**
```bash
aws ec2 describe-vpcs --filters Name=isDefault,Values=true \
  --query "Vpcs[0].VpcId" --output text --region sa-east-1

aws ec2 describe-subnets --filters Name=vpc-id,Values=SEU_VPC_ID \
  --query "Subnets[*].SubnetId" --output text --region sa-east-1
```

**10. Criar Security Group**
```bash
aws ec2 create-security-group \
  --group-name buscador-sg \
  --description "Security group para buscador de noticias" \
  --vpc-id SEU_VPC_ID --region sa-east-1

# Liberar portas
aws ec2 authorize-security-group-ingress \
  --group-id SEU_SG_ID --protocol tcp --port 80 --cidr 0.0.0.0/0 --region sa-east-1

aws ec2 authorize-security-group-ingress \
  --group-id SEU_SG_ID --protocol tcp --port 8000 --cidr 0.0.0.0/0 --region sa-east-1
```

**11. Criar Load Balancer**
```bash
aws elbv2 create-load-balancer \
  --name buscador-lb \
  --subnets SUBNET_1 SUBNET_2 SUBNET_3 \
  --security-groups SEU_SG_ID --region sa-east-1
```

**12. Criar Target Group**
```bash
aws elbv2 create-target-group \
  --name buscador-tg \
  --protocol HTTP \
  --port 8000 \
  --vpc-id SEU_VPC_ID \
  --target-type ip \
  --health-check-path / --region sa-east-1
```

**13. Criar Listener**
```bash
aws elbv2 create-listener \
  --load-balancer-arn SEU_LB_ARN \
  --protocol HTTP --port 80 \
  --default-actions Type=forward,TargetGroupArn=SEU_TG_ARN \
  --region sa-east-1
```

**14. Criar serviço ECS com 3 réplicas**
```bash
aws ecs create-service \
  --cluster buscador-cluster \
  --service-name buscador-service \
  --task-definition buscador-noticias:1 \
  --desired-count 3 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[SUBNET_1,SUBNET_2,SUBNET_3],securityGroups=[SEU_SG_ID],assignPublicIp=ENABLED}" \
  --load-balancers "targetGroupArn=SEU_TG_ARN,containerName=buscador-noticias,containerPort=8000" \
  --region sa-east-1
```

### O que cada serviço AWS faz

| Serviço | O que é | Para que serve no projeto |
|---------|---------|--------------------------|
| ECR | Repositório de imagens Docker | Guarda a imagem da aplicação |
| ECS Fargate | Serviço de containers serverless | Roda os 3 containers sem precisar gerenciar servidores |
| ALB | Application Load Balancer | Distribui o tráfego entre os 3 containers |
| Target Group | Grupo de destinos do LB | Define quais containers recebem tráfego e faz health check |
| Security Group | Firewall virtual | Controla quais portas aceitam tráfego |
| CloudWatch | Serviço de logs | Armazena logs dos containers em tempo real |
| IAM Role | Permissões | Permite que o ECS acesse o ECR e CloudWatch |

---

## 🇺🇸 English

### About
A real-time news monitoring system powered by Google News RSS. Register topics of interest and the system automatically fetches the latest news, stores everything in a database, and exposes it through a REST API — deployed on AWS ECS Fargate with Application Load Balancer across 3 replicas.

### Architecture
```
User → ALB (port 80) → Target Group → 3 ECS Fargate containers → FastAPI
```

### Quick Deploy
```bash
# Build and push to ECR
docker build -t buscador-noticias .
docker tag buscador-noticias:latest ACCOUNT_ID.dkr.ecr.sa-east-1.amazonaws.com/buscador-noticias:latest
docker push ACCOUNT_ID.dkr.ecr.sa-east-1.amazonaws.com/buscador-noticias:latest

# Deploy to ECS with 3 replicas
aws ecs create-service --desired-count 3 --launch-type FARGATE ...
```

---

## 📄 License
MIT License — feel free to use and modify.