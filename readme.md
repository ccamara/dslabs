# Carlos' Data Lab

## Environments

This repo uses `renv` for R notebooks, and a conda environment for python notebooks.

### Creating the virtual environment

To recreate the virtual environment from `environment.yml`, run the following command:

``` bash
conda env create -f environment.yml
```

or, if we want to install the environment within the project:

``` bash
conda env create --prefix env -f environment.yml
```

### Activating the virtual environment

Once the environment has been created, it needs to be activated by typing the following command

``` bash
conda activate dslabs
```

or, if it is stored in `env/` folder:

``` bash
conda activate env/
```

### Publish site

```         
quarto publish gh-pages
```
