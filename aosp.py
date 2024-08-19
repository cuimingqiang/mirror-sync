from gitlab import Gitlab
import json
import os
gl = Gitlab('http://192.168.31.164:9980', private_token='glpat-2KF3rChcSNjPzsMxuDXF', keep_base_url=True)
aosp_mirror_path = "/home/backup/mirror/aosp"
ssh = "ssh://git@192.168.31.164:9922"

def get_remote_aosp():
    groups = gl.groups.list(all=True)
    top_level_groups = [g for g in groups if not g.parent_id]
    for group in top_level_groups:
        if group.name == 'aosp':
            return group
    return None


def traverse_remote_aosp_projects(root_group, aosp_projects):
    if root_group is None:
        return
    subgroups = root_group.subgroups.list(all=True)
    if subgroups is not None:
        for subgroup in subgroups:
            traverse_remote_aosp_projects(gl.groups.get(subgroup.id), aosp_projects)
    projects = root_group.projects.list(all=True)
    for project in projects:
        name = project.name
        path = project.path_with_namespace
        name_with_namespace = project.name_with_namespace
        # print(f"name: {name}, path: {path}, name_with_namespace:{name_with_namespace}")
        aosp_projects[path + ".git"] = name


def parse_remote_aosp():
    aosp_group = get_remote_aosp()
    aosp_projects = {}
    traverse_remote_aosp_projects(aosp_group, aosp_projects)
    # print(aosp_projects)
    with open("aosp_remote.txt", "w+") as mapping:
        # for project in aosp_projects:
        #     mapping.write("name=%s, path=%s.git" % (project["name"], project["path"]))
        mapping.write(json.dumps(aosp_projects, indent=4, ensure_ascii=False))
        mapping.flush()
        mapping.close()


def traverse_local_aosp_projects(rootdir, aosp_projects):
    for subdir in os.listdir(rootdir):
        if subdir != ".repo":
            print(subdir)
            fullpath = rootdir + "/" + subdir
            if subdir.endswith(".git"):
                relationpath = fullpath[len(aosp_mirror_path) + 1 : len(fullpath)]
                # print(relationpath, fullpath)
                aosp_projects["aosp/" + relationpath] = fullpath
            else:
                traverse_local_aosp_projects(fullpath, aosp_projects=aosp_projects)


def parse_local_aosp():
    aosp_projects = {}
    traverse_local_aosp_projects(aosp_mirror_path, aosp_projects=aosp_projects)
    with open("aosp_local.txt", "w+") as mapping:
        # for project in aosp_projects:
        #     mapping.write("name=%s, path=%s.git" % (project["name"], project["path"]))
        mapping.write(json.dumps(aosp_projects, indent=4, ensure_ascii=False))
        mapping.flush()
        mapping.close()


def parse_aosp():
    parse_remote_aosp()
    parse_local_aosp()


def diff_aosp():
    with open("aosp_remote.txt", "r") as mapping:
        remote_aosp_projects = json.loads(mapping.read())
    with open("aosp_local.txt", "r") as mapping:
        local_aosp_projects = json.loads(mapping.read())
    aosp_projects = {}
    left_aosp_projects = {}
    for key, value in local_aosp_projects.items():
        print(key, value)
        if remote_aosp_projects.get(key) is not None:
            aosp_projects[key] = value
            remote_aosp_projects.pop(key)
        else:   
            left_aosp_projects[key] = value
    # print(aosp_projects)
    # print(left_aosp_projects)
    # print(remote_aosp_projects)
    with open("git_need_sync.txt", "w+") as mapping:
        for key, value in aosp_projects.items():
            mapping.write("%s=%s/%s\n" % (value, ssh, key))
        mapping.flush()
        mapping.close()
    with open("git_remote.txt", "w+") as mapping:
        for key, value in left_aosp_projects.items():
            mapping.write("%s=%s/%s\n" % (value, ssh, key))
        mapping.flush()
        mapping.close()
    with open("git_gitlab.txt", "w+") as mapping:
        for key, value in remote_aosp_projects.items():
            mapping.write("%s=%s/%s\n" % (value, ssh, key))
        mapping.flush()
        mapping.close()


if __name__ == "__main__":
    # parse_aosp()
    diff_aosp()