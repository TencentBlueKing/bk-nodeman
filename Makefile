version ?= "dev"
image_repo ?= "mirrors.tencent.com/nodeman"
bkapp_run_env ?= "ee"


build-family-bucket:
	docker build -f support-files/kubernetes/images/family_bucket/Dockerfile -t ${image_repo}/bk-nodeman:${version} --build-arg BKAPP_RUN_ENV=${bkapp_run_env} .

push-family-bucket:
	docker push ${image_repo}/bk-nodeman:${version}
